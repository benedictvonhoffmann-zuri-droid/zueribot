#!/usr/bin/env python3
"""Quartierspiegel ingester — Statistik Stadt Zürich per-quartier profiles.

Each of Zürich's 34 statistical Quartiere has a yearly Quartierspiegel PDF
(plus a city-wide Stadtspiegel = code 000). The HTML landing pages are
JS-hydrated stubs that contain almost no content — the real material is
the PDF linked from the page. So the flow is:

    Playwright the landing page  ->  find latest PDF URL
    Download the PDF             ->  extract text with pypdf
    Chunk as article             ->  write .jsonl

Each quartier is one document with ``district``, ``entity_name`` set and
``category=neighborhoods``.

Usage:
    python -m scripts.ingest.quartierspiegel --dry-run
    python -m scripts.ingest.quartierspiegel --limit 2
    python -m scripts.ingest.quartierspiegel
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

from backend.kb.chunker import Document, chunk_document
from backend.kb.fetchers import Fetcher
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT, PROJECT_ROOT

logger = logging.getLogger("zuribot.kb.ingest.quartierspiegel")

SOURCE_NAME = "Quartierspiegel — Statistik Stadt Zürich"
SOURCE_SLUG = "quartierspiegel"
CATEGORY = "neighborhoods"
AUTHORITY = "city"
LANGUAGE = "de"
TTL_DAYS = 365
LICENSE = "proprietary-cited"

LANDING_BASE = (
    "https://www.stadt-zuerich.ch/de/politik-und-verwaltung/"
    "statistik-und-daten/publikationen-und-dienstleistungen/"
    "publikationen/quartierspiegel/quartier-{code}.html"
)
PDF_DIR = PROJECT_ROOT / "data" / "quartierspiegel_pdfs"

# (code, name, kreis or None for city-wide)
# Codes are stable Stadtquartier statistical IDs.
QUARTIERE: list[tuple[str, str, Optional[int]]] = [
    ("000", "Stadt Zürich (Stadtspiegel)", None),
    # Kreis 1
    ("011", "Rathaus", 1),
    ("012", "Hochschulen", 1),
    ("013", "Lindenhof", 1),
    ("014", "City", 1),
    # Kreis 2
    ("021", "Wollishofen", 2),
    ("023", "Leimbach", 2),
    ("024", "Enge", 2),
    # Kreis 3
    ("031", "Alt-Wiedikon", 3),
    ("033", "Friesenberg", 3),
    ("034", "Sihlfeld", 3),
    # Kreis 4
    ("041", "Werd", 4),
    ("042", "Langstrasse", 4),
    ("044", "Hard", 4),
    # Kreis 5
    ("051", "Gewerbeschule", 5),
    ("052", "Escher Wyss", 5),
    # Kreis 6
    ("061", "Unterstrass", 6),
    ("063", "Oberstrass", 6),
    # Kreis 7
    ("071", "Fluntern", 7),
    ("072", "Hottingen", 7),
    ("073", "Hirslanden", 7),
    ("074", "Witikon", 7),
    # Kreis 8
    ("081", "Seefeld", 8),
    ("082", "Mühlebach", 8),
    ("083", "Weinegg", 8),
    # Kreis 9
    ("091", "Albisrieden", 9),
    ("092", "Altstetten", 9),
    # Kreis 10
    ("101", "Höngg", 10),
    ("102", "Wipkingen", 10),
    # Kreis 11
    ("111", "Affoltern", 11),
    ("112", "Oerlikon", 11),
    ("115", "Seebach", 11),
    # Kreis 12
    ("121", "Saatlen", 12),
    ("122", "Schwamendingen-Mitte", 12),
    ("123", "Hirzenbach", 12),
]


# ── PDF discovery + download ───────────────────────────────────────────────

_PDF_HREF_RE = re.compile(
    r'href="(/[^"]*/quartierspiegel/pdf/[^"]+\.pdf)"',
    re.IGNORECASE,
)


def _discover_pdf_url(fetcher: Fetcher, landing_url: str) -> Optional[str]:
    res = fetcher.fetch_rendered(landing_url, wait_until="networkidle", wait_ms=1500)
    if not res or res.status_code != 200:
        logger.warning("landing fetch failed %s", landing_url)
        return None
    matches = _PDF_HREF_RE.findall(res.content.decode("utf-8", "replace"))
    if not matches:
        return None
    # Prefer most recent year in the filename (e.g. _2025.pdf > _2024.pdf).
    matches = sorted(set(matches))

    def year_key(href: str) -> int:
        m = re.search(r"(\d{4})\.pdf$", href)
        return int(m.group(1)) if m else 0

    best = max(matches, key=year_key)
    return urljoin(landing_url, best)


def _download_pdf(pdf_url: str, dest: Path, timeout: int = 60) -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(pdf_url, timeout=timeout, stream=True)
        r.raise_for_status()
        with dest.open("wb") as f:
            for ch in r.iter_content(chunk_size=64 * 1024):
                if ch:
                    f.write(ch)
        return True
    except Exception as e:
        logger.warning("pdf download failed %s: %s", pdf_url, e)
        return False


def _extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning("page %d extraction failed in %s: %s",
                           i + 1, pdf_path.name, e)
            continue
        text = re.sub(r"-\n(\w)", r"\1", text)
        text = re.sub(r"(\S)\n(\S)", r"\1 \2", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────

def _ingest_one(
    fetcher: Fetcher,
    code: str,
    name: str,
    kreis: Optional[int],
    dry_run: bool,
) -> dict:
    landing = LANDING_BASE.format(code=code)
    pdf_url = _discover_pdf_url(fetcher, landing)
    if not pdf_url:
        logger.warning("no PDF discovered for code=%s (%s)", code, name)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    pdf_path = PDF_DIR / f"quartier-{code}.pdf"
    if not _download_pdf(pdf_url, pdf_path):
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    text = _extract_pdf_text(pdf_path)
    if len(text) < 1000:
        logger.warning("extracted text too short (%d chars) for %s", len(text), name)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    logger.info("code=%s %s — pdf=%s, %d chars", code, name, pdf_url, len(text))
    if dry_run:
        return {"docs_written": 0, "total_chunks": 0, "skipped": 0}

    today = date.today()
    title = (
        f"Quartierspiegel {name}" if kreis is not None
        else "Stadtspiegel Zürich"
    )
    district = f"Kreis {kreis}" if kreis is not None else None
    tags = ["quartierspiegel", "statistik"]
    if kreis is not None:
        tags.append(f"kreis-{kreis}")

    doc = Document(
        source_url=landing,
        source_name=SOURCE_NAME,
        title=title,
        language=LANGUAGE,
        category=CATEGORY,  # type: ignore[arg-type]
        authority=AUTHORITY,  # type: ignore[arg-type]
        doc_type="article",  # type: ignore[arg-type]
        text=text,
        tags=tags,
        created_at=today,
        updated_at=today,
        ttl_days=TTL_DAYS,
        license=LICENSE,
        district=district,
        entity_name=name,
    )
    try:
        chunks: list[Chunk] = chunk_document(doc)
    except Exception as e:
        logger.warning("chunk failed code=%s: %s", code, e)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 1}

    write_chunks(chunks, CHUNKS_ROOT, CATEGORY, SOURCE_SLUG)
    return {"docs_written": 1, "total_chunks": len(chunks), "skipped": 0}


def run(limit: int, dry_run: bool, only_code: Optional[str]) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    items = QUARTIERE
    if only_code:
        items = [q for q in items if q[0] == only_code]
    if limit:
        items = items[:limit]

    logger.info("Processing %d Quartiere (dry_run=%s)", len(items), dry_run)

    grand = {"docs_written": 0, "total_chunks": 0, "skipped": 0}
    with Fetcher(rate_limit_seconds=1.5, timeout=30) as fetcher:
        for code, name, kreis in items:
            stats = _ingest_one(fetcher, code, name, kreis, dry_run)
            for k in grand:
                grand[k] += stats[k]

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Stadt Zürich Quartierspiegel PDFs"
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--code", type=str, default=None,
                        help="Process a single quartier code (e.g. 011)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run, only_code=args.code)


if __name__ == "__main__":
    sys.exit(main())
