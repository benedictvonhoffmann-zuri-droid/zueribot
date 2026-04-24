#!/usr/bin/env python3
"""Federal law PDF ingester — Phase 1 schema.

Reads hand-downloaded Fedlex PDFs (Bundesverfassung, OR, ZGB, StGB,
StPO, ZPO, VRV, VTS) and emits one chunk per article (spec §5.3:
statute -> one article = one chunk, split on Absatz if >2000 tokens).

PDFs live in ``data/law_pdfs/`` (gitignored). Filenames are matched
against ``LAW_METADATA`` for SR number, abbreviation, and canonical
law name.

Usage:
    python -m scripts.ingest.law_pdfs --dry-run
    python -m scripts.ingest.law_pdfs --pdf-dir /path/to/pdfs
    python -m scripts.ingest.law_pdfs --limit 1     # one PDF smoke test
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from backend.kb.chunker import Document, chunk_document
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT, PROJECT_ROOT

logger = logging.getLogger("zuribot.kb.ingest.law_pdfs")

SOURCE_SLUG = "fedlex"
AUTHORITY = "federal"
CATEGORY = "law"
DOC_TYPE = "statute"
LANGUAGE = "de"
LICENSE = "public-domain"  # federal law is public domain in CH
TTL_DAYS = 365

DEFAULT_PDF_DIR = PROJECT_ROOT / "data" / "law_pdfs"

# Map normalised filename stem → law metadata + fedlex URL.
# The normaliser lowercases and replaces spaces/dashes with underscores,
# then picks the first matching prefix.
LAW_METADATA: dict[str, dict[str, str]] = {
    "bundesverfassung": {
        "name": "Bundesverfassung der Schweizerischen Eidgenossenschaft",
        "abbrev": "BV",
        "sr": "101",
        "url": "https://www.fedlex.admin.ch/eli/cc/1999/404/de",
    },
    "obligationenrecht": {
        "name": "Schweizerisches Obligationenrecht",
        "abbrev": "OR",
        "sr": "220",
        "url": "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de",
    },
    "zivilgesetzbuch": {
        "name": "Schweizerisches Zivilgesetzbuch",
        "abbrev": "ZGB",
        "sr": "210",
        "url": "https://www.fedlex.admin.ch/eli/cc/24/233_245_233/de",
    },
    "strafgesetzbuch": {
        "name": "Schweizerisches Strafgesetzbuch",
        "abbrev": "StGB",
        "sr": "311.0",
        "url": "https://www.fedlex.admin.ch/eli/cc/54/757_781_799/de",
    },
    "strafprozessordnung": {
        "name": "Schweizerische Strafprozessordnung",
        "abbrev": "StPO",
        "sr": "312.0",
        "url": "https://www.fedlex.admin.ch/eli/cc/2010/267/de",
    },
    "zivilprozessordnung": {
        "name": "Schweizerische Zivilprozessordnung",
        "abbrev": "ZPO",
        "sr": "272",
        "url": "https://www.fedlex.admin.ch/eli/cc/2010/262/de",
    },
    "verkehrsregelnverordnung": {
        "name": "Verkehrsregelnverordnung",
        "abbrev": "VRV",
        "sr": "741.11",
        "url": "https://www.fedlex.admin.ch/eli/cc/1963/741_763_779/de",
    },
    "verordnung_ueber_die_technischen_anforderungen_an_strassenfahrzeuge": {
        "name": "Verordnung über die technischen Anforderungen an Strassenfahrzeuge",
        "abbrev": "VTS",
        "sr": "741.41",
        "url": "https://www.fedlex.admin.ch/eli/cc/1995/4425_4425_4425/de",
    },
}


def _normalise_stem(filename: str) -> str:
    stem = Path(filename).stem.lower()
    stem = stem.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    stem = re.sub(r"[\s\-]+", "_", stem)
    stem = re.sub(r"[^a-z0-9_]", "", stem)
    return stem


def _match_metadata(filename: str) -> Optional[dict[str, str]]:
    stem = _normalise_stem(filename)
    # Prefer exact prefix match on the longest key so e.g.
    # "verordnung_ueber_die_technischen_..." wins over "verordnung".
    for key in sorted(LAW_METADATA, key=len, reverse=True):
        if stem.startswith(key):
            return LAW_METADATA[key]
    return None


# ── PDF text extraction ────────────────────────────────────────────────────

def _extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning("page %d extraction failed in %s: %s", i + 1, pdf_path.name, e)
            continue
        # Join hyphenated line-break words.
        text = re.sub(r"-\n(\w)", r"\1", text)
        # Collapse mid-sentence line breaks to spaces.
        text = re.sub(r"(\S)\n(\S)", r"\1 \2", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text and not _is_index_page(text):
            parts.append(text)
    return "\n\n".join(parts)


def _is_index_page(text: str) -> bool:
    """Heuristic: TOC / footnote pages have short lines and many refs."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 4:
        return False
    short = sum(1 for l in lines if len(l.split()) < 6)
    refs = sum(1 for l in lines if re.match(r"^(Art\.|§|\d+\.?\s|AS \d|SR \d|BBl )", l))
    return (short / len(lines) > 0.70) and (refs / len(lines) > 0.40)


# ── Article splitting ──────────────────────────────────────────────────────

# Match "Art. 12", "Art. 12a", "Artikel 5" at the start of a line.
_ARTICLE_RE = re.compile(
    r"^\s*(?:Art\.|Artikel)\s+(\d+[a-z]?(?:bis|ter|quater|quinquies|sexies)?)\b",
    re.MULTILINE,
)


def _split_articles(text: str) -> list[tuple[str, str]]:
    """Return list of (article_number, article_text). Text before the first
    article (title page, preamble) is bundled into a synthetic 'preamble'."""
    matches = list(_ARTICLE_RE.finditer(text))
    if not matches:
        return [("preamble", text.strip())]

    out: list[tuple[str, str]] = []
    first_start = matches[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if len(preamble) > 200:
            out.append(("preamble", preamble))

    for i, m in enumerate(matches):
        art_no = m.group(1)
        body_start = m.start()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            out.append((art_no, body))
    return out


# ── Main ──────────────────────────────────────────────────────────────────

def _ingest_one(pdf_path: Path, dry_run: bool) -> dict:
    meta = _match_metadata(pdf_path.name)
    if not meta:
        logger.warning("no metadata match for %s — skipping", pdf_path.name)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    logger.info("Processing %s (%s, SR %s)", pdf_path.name, meta["abbrev"], meta["sr"])

    text = _extract_pdf_text(pdf_path)
    if not text:
        logger.warning("no text extracted from %s", pdf_path.name)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    articles = _split_articles(text)
    logger.info("  %d articles detected, %d chars", len(articles), len(text))

    if dry_run:
        return {"docs_written": 0, "total_chunks": 0, "skipped": 0}

    today = date.today()
    docs_written = 0
    total_chunks = 0

    for art_no, body in articles:
        doc_title = f"{meta['abbrev']} Art. {art_no}" if art_no != "preamble" else f"{meta['abbrev']} — Präambel"
        # Per-article fragment keeps doc_id unique (make_doc_id hashes source_url).
        frag = "preamble" if art_no == "preamble" else f"art-{art_no}"
        doc = Document(
            source_url=f"{meta['url']}#{frag}",
            source_name=f"Fedlex — {meta['abbrev']}",
            title=doc_title,
            language=LANGUAGE,
            category=CATEGORY,  # type: ignore[arg-type]
            authority=AUTHORITY,  # type: ignore[arg-type]
            doc_type=DOC_TYPE,  # type: ignore[arg-type]
            text=body,
            subcategory=None,
            tags=[meta["abbrev"].lower()],
            created_at=today,
            updated_at=today,
            ttl_days=TTL_DAYS,
            license=LICENSE,
            law_name=meta["name"],
            abbrev=meta["abbrev"],
            sr_number=meta["sr"],
            article_number=None if art_no == "preamble" else art_no,
        )
        try:
            chunks: list[Chunk] = chunk_document(doc)
        except Exception as e:
            logger.warning("chunk failed %s Art. %s: %s", meta["abbrev"], art_no, e)
            continue

        write_chunks(chunks, CHUNKS_ROOT, CATEGORY, SOURCE_SLUG)
        docs_written += 1
        total_chunks += len(chunks)

    logger.info("  wrote %d docs / %d chunks", docs_written, total_chunks)
    return {"docs_written": docs_written, "total_chunks": total_chunks, "skipped": 0}


def run(pdf_dir: Path, limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not pdf_dir.exists():
        logger.error("PDF dir not found: %s", pdf_dir)
        return 1

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if limit:
        pdfs = pdfs[:limit]
    if not pdfs:
        logger.error("no PDFs in %s", pdf_dir)
        return 1

    logger.info("Found %d PDFs in %s", len(pdfs), pdf_dir)

    grand = {"docs_written": 0, "total_chunks": 0, "skipped": 0}
    for pdf in pdfs:
        stats = _ingest_one(pdf, dry_run)
        for k in grand:
            grand[k] += stats[k]

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest federal law PDFs")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR,
                        help=f"Directory containing PDFs (default: {DEFAULT_PDF_DIR})")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N PDFs (0 = all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show matches, don't write chunks")
    args = parser.parse_args()
    return run(pdf_dir=args.pdf_dir, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
