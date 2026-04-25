#!/usr/bin/env python3
"""Stadtarchiv / Zürichs Geschichte ingester — historical character layer.

Crawls the ``/de/stadtleben/stadtportraet/zuerichs-geschichte/*`` subtree
on stadt-zuerich.ch — Stadtarchiv, Baugeschichtliches Archiv,
Archäologie, digitale Zeitreise, Erinnerungskultur, Beflaggung. These
pages document Zürich's history and shape Bünzli's voice (spec §1,
§11.8). Per spec §11, ⭐ priority character source.

Emits ``doc_type=historical`` (smaller chunks, 300-400 tokens) and
``subcategory=leisure/history``. Although these URLs technically fall
under stadt_zuerich.py's allowlist, that ingester emits ``article``s —
this script overrides with the historical type.

Plain HTTP works (the site server-renders enough text); Playwright
isn't needed here. We reuse the stzh HTML normaliser from
stadt_zuerich.py to handle the bogus "Navigation" h1 and stzh-* web
components.

Usage:
    python -m scripts.ingest.stadtarchiv --dry-run
    python -m scripts.ingest.stadtarchiv --limit 5
    python -m scripts.ingest.stadtarchiv
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from typing import Optional

from backend.kb.chunker import Document, chunk_document
from backend.kb.fetchers import Fetcher
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import (
    CHUNKS_ROOT,
    CrawlConfig,
    crawl,
    extract_title_and_sections,
)
from scripts.ingest.stadt_zuerich import _normalise_stzh_html

logger = logging.getLogger("zuribot.kb.ingest.stadtarchiv")

SOURCE_NAME = "Stadtarchiv Zürich"
SOURCE_SLUG = "stadtarchiv"
CATEGORY = "leisure"
SUBCATEGORY = "leisure/history"
AUTHORITY = "city"
LANGUAGE = "de"
TTL_DAYS = None  # historical content is stable
LICENSE = "proprietary-cited"

URL_PREFIX = (
    "https://www.stadt-zuerich.ch/de/stadtleben/stadtportraet/zuerichs-geschichte"
)
SEEDS = [
    URL_PREFIX + ".html",
    URL_PREFIX + "/stadtarchiv.html",
    URL_PREFIX + "/baz.html",
    URL_PREFIX + "/archaeologie.html",
    URL_PREFIX + "/digitale-zeitreise.html",
    URL_PREFIX + "/erinnerungskultur.html",
    URL_PREFIX + "/beflaggung.html",
]


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (title + " " + text[:600]).lower()
    for kw in (
        "archiv", "geschichte", "mittelalter", "reformation", "limmat",
        "altstadt", "denkmal", "museum", "jahrhundert", "ausgrabung",
        "manesse", "zwingli", "guilden",
    ):
        if kw in t:
            tags.append(kw)
    return tags


def _heuristic_period(text: str) -> Optional[str]:
    """Best-effort century extraction from the first 800 chars."""
    sample = text[:800].lower()
    for needle, label in (
        ("römisch", "Antike / Römerzeit"),
        ("mittelalter", "Mittelalter"),
        ("reformation", "16. Jahrhundert"),
        ("19. jahrhundert", "19. Jahrhundert"),
        ("20. jahrhundert", "20. Jahrhundert"),
    ):
        if needle in sample:
            return label
    return None


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cfg = CrawlConfig(
        seeds=SEEDS,
        url_prefix=URL_PREFIX,
        max_pages=limit if limit else 60,
        max_depth=2,
        render=False,
    )

    logger.info("Stadtarchiv crawl — seeds=%d, max=%d", len(SEEDS), cfg.max_pages)
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawled %d pages.", len(results))

    if dry_run:
        for r in results:
            logger.info("  %s", r.url)
        return 0

    today = date.today()
    docs_written = 0
    total_chunks = 0

    for res in results:
        try:
            html = _normalise_stzh_html(res.content)
        except Exception as e:
            logger.warning("normalise failed url=%s err=%s", res.url, e)
            continue

        title, sections, full_text = extract_title_and_sections(html)
        if not title or len(full_text) < 400:
            logger.info("skip (sparse) url=%s text=%d", res.url, len(full_text))
            continue

        period = _heuristic_period(full_text)

        doc = Document(
            source_url=res.final_url or res.url,
            source_name=SOURCE_NAME,
            title=title,
            language=LANGUAGE,
            category=CATEGORY,  # type: ignore[arg-type]
            authority=AUTHORITY,  # type: ignore[arg-type]
            doc_type="historical",  # type: ignore[arg-type]
            sections=sections,
            subcategory=SUBCATEGORY,
            tags=_tags_for(title, full_text),
            created_at=today,
            updated_at=today,
            ttl_days=TTL_DAYS,
            license=LICENSE,
            period=period,
        )
        try:
            chunks: list[Chunk] = chunk_document(doc)
        except Exception as e:
            logger.warning("chunk failed url=%s err=%s", res.url, e)
            continue

        write_chunks(chunks, CHUNKS_ROOT, CATEGORY, SOURCE_SLUG)
        docs_written += 1
        total_chunks += len(chunks)

    logger.info("Total: docs=%d chunks=%d", docs_written, total_chunks)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Stadtarchiv / Zürichs Geschichte")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
