#!/usr/bin/env python3
"""Wikipedia ingester — curated Zürich list.

Fills three gaps in one shot: ``neighborhoods`` (Kreise + Quartiere),
``leisure`` with ``historical`` doc_type (landmarks, festivals — the
character-shaping layer per spec §1 and memory), and EN coverage for
expats (audit flagged <0.2% of old KB).

Content comes from Wikipedia's REST API (`/page/html/{title}`) —
clean Parsoid HTML, no scraping. We strip Wikipedia's structural
noise (infoboxes, references, see-also, coordinates, edit-section
links) and feed the rest to the shared heading/paragraph extractor
in ``_base.py``.

Article list is hand-picked. We deliberately do not crawl — the spec
says curate Wikipedia for quality, not bulk.

Usage:
    python -m scripts.ingest.wikipedia --dry-run
    python -m scripts.ingest.wikipedia --limit 5
    python -m scripts.ingest.wikipedia                # full curated run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from backend.kb.chunker import Document, chunk_document
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT, extract_title_and_sections

logger = logging.getLogger("zuribot.kb.ingest.wikipedia")

SOURCE_SLUG = "wikipedia"
AUTHORITY = "wikipedia"
TTL_DAYS = 365
LICENSE = "CC-BY-SA"
USER_AGENT = (
    "BuenzliBot/0.1 (https://buenzli.space/bot; knowledge base ingestion)"
)

# (title, category, doc_type, language, optional district)
# doc_type="historical" triggers smaller (300-400 token) chunking per spec §5.3
CURATED: list[tuple[str, str, str, str, Optional[str]]] = [
    # neighborhoods — Kreise + notable Quartiere
    ("Zürich", "neighborhoods", "article", "de", None),
    ("Kreis 1 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 1"),
    ("Kreis 2 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 2"),
    ("Kreis 3 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 3"),
    ("Kreis 4 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 4"),
    ("Kreis 5 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 5"),
    ("Kreis 6 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 6"),
    ("Kreis 7 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 7"),
    ("Kreis 8 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 8"),
    ("Kreis 9 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 9"),
    ("Kreis 10 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 10"),
    ("Kreis 11 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 11"),
    ("Kreis 12 (Stadt Zürich)", "neighborhoods", "article", "de", "Kreis 12"),
    ("Langstrasse", "neighborhoods", "article", "de", "Kreis 4"),
    ("Seefeld (Zürich)", "neighborhoods", "article", "de", "Kreis 8"),
    ("Zürich-West", "neighborhoods", "article", "de", "Kreis 5"),
    ("Wiedikon", "neighborhoods", "article", "de", "Kreis 3"),
    ("Wipkingen", "neighborhoods", "article", "de", "Kreis 10"),
    ("Oerlikon", "neighborhoods", "article", "de", "Kreis 11"),
    ("Altstetten", "neighborhoods", "article", "de", "Kreis 9"),

    # leisure/historical — landmarks, geography (character-shaping)
    ("Zürichsee", "leisure", "historical", "de", None),
    ("Limmat", "leisure", "historical", "de", None),
    ("Uetliberg", "leisure", "historical", "de", None),
    ("Zürichberg", "leisure", "historical", "de", None),
    ("Grossmünster", "leisure", "historical", "de", "Kreis 1"),
    ("Fraumünster", "leisure", "historical", "de", "Kreis 1"),
    ("Hauptbahnhof Zürich", "leisure", "historical", "de", "Kreis 1"),
    ("Bahnhofstrasse (Zürich)", "leisure", "historical", "de", "Kreis 1"),
    ("Kunsthaus Zürich", "leisure", "historical", "de", "Kreis 1"),
    ("Opernhaus Zürich", "leisure", "historical", "de", "Kreis 1"),
    ("Schauspielhaus Zürich", "leisure", "historical", "de", None),
    ("Schweizerisches Nationalmuseum", "leisure", "historical", "de", "Kreis 1"),
    ("Zoo Zürich", "leisure", "historical", "de", "Kreis 7"),
    ("Tonhalle Zürich", "leisure", "historical", "de", "Kreis 2"),
    ("Geschichte der Stadt Zürich", "leisure", "historical", "de", None),

    # leisure — festivals (article, not historical — they're recurring)
    ("Street Parade", "leisure", "article", "de", None),
    ("Sechseläuten", "leisure", "article", "de", None),
    ("Züri Fäscht", "leisure", "article", "de", None),
    ("Zurich Film Festival", "leisure", "article", "de", None),

    # education — major universities
    ("Universität Zürich", "education", "article", "de", None),
    ("ETH Zürich", "education", "article", "de", None),

    # mobility — backbone operators
    ("Verkehrsbetriebe Zürich", "mobility", "article", "de", None),
    ("S-Bahn Zürich", "mobility", "article", "de", None),

    # civic — canton background
    ("Kanton Zürich", "civic", "article", "de", None),

    # EN coverage — small but strategic
    ("Zürich", "neighborhoods", "article", "en", None),
    ("Swiss German", "civic", "article", "en", None),
    ("History of Zürich", "leisure", "historical", "en", None),
    ("Old Swiss Confederacy", "leisure", "historical", "en", None),
]


# Sections on WP pages whose headings indicate ignorable tails.
_STRIP_HEADINGS = {
    "einzelnachweise", "literatur", "weblinks", "siehe auch",
    "references", "external links", "see also", "bibliography",
    "notes", "further reading", "sources", "fussnoten",
}


def _wp_url(title: str, lang: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def _fetch_html(title: str, lang: str, timeout: int = 30) -> Optional[str]:
    """Fetch Parsoid HTML for ``title`` from ``{lang}.wikipedia.org``."""
    api = f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{quote(title.replace(' ', '_'))}"
    try:
        resp = requests.get(api, timeout=timeout, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as e:
        logger.warning("fetch failed [%s] %s: %s", lang, title, e)
        return None
    if resp.status_code == 404:
        logger.info("not found [%s] %s", lang, title)
        return None
    if resp.status_code != 200:
        logger.warning("HTTP %s [%s] %s", resp.status_code, lang, title)
        return None
    return resp.text


def _clean_wikipedia_html(html: str, title: str) -> bytes:
    """Remove Wikipedia-specific noise before handing to the shared extractor.

    Drops infoboxes, references, coordinates, tables of contents, hatnotes,
    edit-links, and sections after "References"/"See also"/"Literatur"/etc.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Drop obvious noise by class/selector.
    noise_selectors = [
        ".infobox", ".navbox", ".sidebar", ".reference", ".mw-editsection",
        ".reflist", "ol.references", ".thumb", ".gallery", ".hatnote",
        ".shortdescription", ".coordinates", ".mw-empty-elt", ".metadata",
        ".mw-cite-backlink", "table.wikitable", "sup.reference",
        ".vertical-navbox", ".portal", ".catlinks", "#toc",
        "figure", "style", "script",
    ]
    for sel in noise_selectors:
        for el in soup.select(sel):
            el.decompose()

    # Strip everything from a "References"-class heading onwards.
    for h in soup.find_all(["h1", "h2", "h3"]):
        label = h.get_text(" ", strip=True).lower().strip()
        if label in _STRIP_HEADINGS:
            # Remove this heading and all following siblings.
            nxt = h.find_next_sibling()
            h.decompose()
            while nxt is not None:
                sib = nxt.find_next_sibling()
                nxt.decompose()
                nxt = sib
            break

    # Wikipedia Parsoid output usually has <section> per h2; make sure the page
    # has an <h1> with the article title so the extractor picks it up.
    if soup.body and not soup.find("h1"):
        h1 = soup.new_tag("h1")
        h1.string = title
        soup.body.insert(0, h1)

    return str(soup).encode("utf-8")


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    items = CURATED[:limit] if limit else CURATED
    logger.info("Processing %d articles (of %d curated).", len(items), len(CURATED))

    if dry_run:
        by_cat: dict[str, int] = {}
        for _, cat, *_ in items:
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            logger.info("  %-14s %3d", cat, n)
        return 0

    today = date.today()
    grand = {"docs_written": 0, "total_chunks": 0, "skipped": 0}

    for title, category, doc_type, lang, district in items:
        src_url = _wp_url(title, lang)
        html = _fetch_html(title, lang)
        if html is None:
            grand["skipped"] += 1
            continue
        cleaned = _clean_wikipedia_html(html, title)

        page_title, sections, full_text = extract_title_and_sections(cleaned)
        if not page_title:
            page_title = title
        if len(full_text) < 400:
            logger.info("skip (too short) %s", src_url)
            grand["skipped"] += 1
            continue

        doc = Document(
            source_url=src_url,
            source_name=f"Wikipedia ({lang.upper()})",
            title=page_title,
            language=lang,
            category=category,  # type: ignore[arg-type]
            authority=AUTHORITY,  # type: ignore[arg-type]
            doc_type=doc_type,  # type: ignore[arg-type]
            sections=sections,
            subcategory=None,
            tags=[],
            created_at=today,
            updated_at=today,
            ttl_days=TTL_DAYS,
            district=district,
            license=LICENSE,
        )
        try:
            chunks: list[Chunk] = chunk_document(doc)
        except Exception as e:
            logger.warning("chunk failed %s: %s", src_url, e)
            grand["skipped"] += 1
            continue

        write_chunks(chunks, CHUNKS_ROOT, category, SOURCE_SLUG)
        grand["docs_written"] += 1
        grand["total_chunks"] += len(chunks)
        logger.info("  [%s/%s] %s → %d chunks", lang, category, title, len(chunks))

        time.sleep(0.4)  # polite

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest curated Wikipedia articles")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap number of articles (0 = full list)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print category breakdown, don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
