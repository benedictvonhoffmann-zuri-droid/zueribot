#!/usr/bin/env python3
"""Zürich cantonal law (LS / Zürcher Gesetzessammlung) ingester.

The cantonal law corpus is ~150 active statutes listed on zh.ch.
Each statute is metadata on an HTML page linking out to a PDF of the
current in-force text (hosted on notes.zh.ch). This ingester:

    1. Paginates the JSON index (10 pages × 15 entries).
    2. Visits each law's HTML page, extracts the current-PDF URL.
    3. Downloads the PDF, splits on '§ N' article markers, and
       emits one Chunk per paragraph — doc_type=statute,
       authority=cantonal, category=law, ls_number set to the
       Zürich systematic number (e.g. "101", "170.4").

Swiss cantonal law uses '§' not 'Art.' for article markers, so the
splitter differs from the federal (Fedlex) ingester.

Usage:
    python -m scripts.ingest.zh_cantonal_law --dry-run
    python -m scripts.ingest.zh_cantonal_law --limit 3      # smoke test
    python -m scripts.ingest.zh_cantonal_law                # full run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

import requests

from backend.kb.chunker import Document, chunk_document
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT

logger = logging.getLogger("zuribot.kb.ingest.zh_cantonal_law")

SOURCE_SLUG = "zh_cantonal_law"
SOURCE_NAME = "Kanton Zürich — LS"
AUTHORITY = "cantonal"
CATEGORY = "law"
DOC_TYPE = "statute"
LANGUAGE = "de"
LICENSE = "public-domain"
TTL_DAYS = 365

BASE = "https://www.zh.ch"
INDEX_URL = (
    f"{BASE}/de/politik-staat/gesetze-beschluesse/gesetzessammlung/"
    "_jcr_content/main/lawcollectionsearch_312548694.zhweb-zhlex-ls.zhweb-cache.json"
)
USER_AGENT = "Mozilla/5.0 (compatible; BuenzliBot/0.1; +https://buenzli.space/bot) KB-ingest"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.9"}


def _fetch_index() -> list[dict]:
    """Paginate the JSON index — returns all law metadata entries."""
    all_entries: list[dict] = []
    page = 1
    while True:
        url = INDEX_URL if page == 1 else f"{INDEX_URL}?page={page}"
        logger.info("index page %d …", page)
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        doc = resp.json()
        data = doc.get("data") or []
        if not data:
            break
        all_entries.extend(data)
        total_pages = doc.get("numberOfResultPages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.4)
    logger.info("index: %d entries", len(all_entries))
    return all_entries


_PDF_HREF_RE = re.compile(
    r'href="(https://www\.notes\.zh\.ch/appl/zhlex_r\.nsf/OpenAttachment[^"]+\.pdf)"',
)


def _fetch_pdf_url(law_page_url: str) -> Optional[str]:
    """Scrape the current-version PDF URL from a law's HTML detail page."""
    resp = requests.get(law_page_url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        logger.warning("law page HTTP %s: %s", resp.status_code, law_page_url)
        return None
    m = _PDF_HREF_RE.search(resp.text)
    return m.group(1) if m else None


_JS_REDIR_RE = re.compile(r'window\.location="([^"]+)"')


def _fetch_pdf(pdf_url: str, cache_dir: Path) -> Optional[Path]:
    """Download a PDF to ``cache_dir`` (keyed by URL hash).

    ``notes.zh.ch`` responds to ``OpenAttachment?…`` with a short HTML
    document containing a JS ``window.location`` redirect to the real
    ``$File/…pdf`` URL, so we follow that manually when the body looks
    like the stub HTML instead of a PDF.
    """
    import hashlib
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(pdf_url.encode()).hexdigest()[:16]
    path = cache_dir / f"{key}.pdf"
    if path.exists() and path.stat().st_size > 1024:
        return path

    resp = requests.get(pdf_url, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        logger.warning("pdf HTTP %s: %s", resp.status_code, pdf_url)
        return None

    # notes.zh.ch JS redirect → follow to the real file URL.
    if resp.headers.get("Content-Type", "").startswith("text/html"):
        m = _JS_REDIR_RE.search(resp.text)
        if not m:
            logger.warning("no JS redirect in stub html: %s", pdf_url)
            return None
        target = m.group(1)
        if target.startswith("/"):
            from urllib.parse import urlparse, urlunparse
            p = urlparse(pdf_url)
            target = urlunparse((p.scheme, p.netloc, target, "", "", ""))
        resp = requests.get(target, headers=HEADERS, timeout=60)
        if resp.status_code != 200:
            logger.warning("pdf (redir) HTTP %s: %s", resp.status_code, target)
            return None

    path.write_bytes(resp.content)
    return path


def _extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        text = re.sub(r"-\n(\w)", r"\1", text)
        # Collapse mid-sentence line breaks, but preserve newlines that
        # precede a section marker (§ N / Art. N / Artikel N) — otherwise
        # _SECTION_RE can't see them and adjacent statute sections get
        # merged into a single oversized chunk.
        text = re.sub(
            r"(\S)\n(?!\s*(?:§|Art\.|Artikel)\s+\d)(\S)",
            r"\1 \2",
            text,
        )
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# Cantonal laws mostly use § but some (Kantonsverfassung, inter-cantonal
# treaties) use Art. Accept both.
_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:§|Art\.|Artikel)\s*(\d+[a-z]?(?:bis|ter|quater)?)\b",
)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Return list of (§-number, section-text). Preamble prefixed."""
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return [("preamble", text.strip())]
    out: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if len(preamble) > 200:
            out.append(("preamble", preamble))
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out.append((num, body))
    return out


def _ingest_one(entry: dict, cache_dir: Path, dry_run: bool) -> dict:
    ls_number = entry["referenceNumber"]
    title = entry["enactmentTitle"]
    law_page = BASE + entry["link"]

    logger.info("LS %s — %s", ls_number, title)
    if dry_run:
        return {"docs_written": 0, "total_chunks": 0, "skipped": 0}

    pdf_url = _fetch_pdf_url(law_page)
    if not pdf_url:
        logger.warning("no PDF link for LS %s", ls_number)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    pdf_path = _fetch_pdf(pdf_url, cache_dir)
    if not pdf_path:
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    text = _extract_pdf_text(pdf_path)
    if not text:
        logger.warning("empty PDF text: LS %s", ls_number)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    sections = _split_sections(text)
    logger.info("  %d sections, %d chars", len(sections), len(text))

    today = date.today()
    docs_written = 0
    total_chunks = 0

    for num, body in sections:
        frag = "preamble" if num == "preamble" else f"para-{num}"
        doc_title = (f"LS {ls_number} § {num}" if num != "preamble"
                     else f"LS {ls_number} — Präambel")
        doc = Document(
            # Fragment keeps doc_id unique across sections of the same law.
            source_url=f"{law_page}#{frag}",
            source_name=f"{SOURCE_NAME} — LS {ls_number}",
            title=doc_title,
            language=LANGUAGE,
            category=CATEGORY,  # type: ignore[arg-type]
            authority=AUTHORITY,  # type: ignore[arg-type]
            doc_type=DOC_TYPE,  # type: ignore[arg-type]
            text=body,
            subcategory=None,
            tags=["cantonal", ls_number.split(".")[0]],
            created_at=today,
            updated_at=today,
            ttl_days=TTL_DAYS,
            license=LICENSE,
            law_name=title,
            ls_number=ls_number,
            article_number=None if num == "preamble" else num,
        )
        try:
            chunks: list[Chunk] = chunk_document(doc)
        except Exception as e:
            logger.warning("chunk failed LS %s § %s: %s", ls_number, num, e)
            continue
        write_chunks(chunks, CHUNKS_ROOT, CATEGORY, SOURCE_SLUG)
        docs_written += 1
        total_chunks += len(chunks)

    logger.info("  wrote %d docs / %d chunks", docs_written, total_chunks)
    return {"docs_written": docs_written, "total_chunks": total_chunks, "skipped": 0}


def run(limit: int, dry_run: bool, cache_dir: Path) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    entries = _fetch_index()
    if limit:
        entries = entries[:limit]

    if dry_run:
        for e in entries[:20]:
            logger.info("  %-10s %s", e["referenceNumber"], e["enactmentTitle"])
        return 0

    grand = {"docs_written": 0, "total_chunks": 0, "skipped": 0}
    for entry in entries:
        stats = _ingest_one(entry, cache_dir, dry_run)
        for k in grand:
            grand[k] += stats[k]
        time.sleep(0.6)  # polite
    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Zürich cantonal law (LS)")
    parser.add_argument("--limit", type=int, default=0, help="Cap laws (0 = all)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-dir", type=Path,
                        default=Path("data/law_pdfs_cache/zh_cantonal"),
                        help="Where to cache downloaded PDFs")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run, cache_dir=args.cache_dir)


if __name__ == "__main__":
    sys.exit(main())
