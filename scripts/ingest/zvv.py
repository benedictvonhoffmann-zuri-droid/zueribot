#!/usr/bin/env python3
"""ZVV ingester — Zürcher Verkehrsverbund (public transport).

Fills the mobility gap with authoritative local-transport content:
tickets, abos, zones, night service, dog/bike rules, refunds.

URL discovery: single sitemap at ``/de.sitemap.xml`` (~700 URLs).
Server-rendered HTML with a proper ``<h1>`` — no DOM surgery needed.

Authority = cantonal (ZVV is a Kanton Zürich transit association).
Everything slots into ``category="mobility"``.

Usage:
    python -m scripts.ingest.zvv --dry-run
    python -m scripts.ingest.zvv --limit 30
    python -m scripts.ingest.zvv                       # full run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from typing import Optional
from urllib.parse import urlparse

import requests

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.zvv")

SOURCE_NAME = "ZVV"
SOURCE_SLUG = "zvv"
AUTHORITY = "cantonal"
CATEGORY = "mobility"
LANGUAGE = "de"
SITEMAP_URL = "https://www.zvv.ch/de.sitemap.xml"
URL_PREFIX = "https://www.zvv.ch/de/"
TTL_DAYS = 180

# Path substrings we always skip — admin/contact/search pages with no KB value.
SKIP_PATH_SUBSTRINGS = (
    "/allgemeine-seiten/",
    "/rechtliches/",
    "/impressum",
    "/datenschutz",
    "/kontakt",
    "/suche",
)


def _fetch_sitemap_urls(timeout: int = 30) -> list[str]:
    logger.info("Fetching %s …", SITEMAP_URL)
    resp = requests.get(SITEMAP_URL, timeout=timeout)
    resp.raise_for_status()
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", resp.text)
    kept = [u for u in urls if _is_allowed(u)]
    logger.info("sitemap: %d URLs, %d kept", len(urls), len(kept))
    return kept


def _is_allowed(url: str) -> bool:
    if not url.startswith(URL_PREFIX):
        return False
    path = urlparse(url).path
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    # Drop top-level landing pages like /de/home.html — low signal.
    if path.count("/") < 3:
        return False
    return True


def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    parts = path.split("/")
    if len(parts) < 1 or not parts[0]:
        return None
    leaf = parts[0].replace("-", "_").replace(".html", "")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:500] + " ").lower()
    for kw in (
        "abo", "ticket", "zone", "nachtnetz", "swisspass", "halbtax",
        "9-uhr", "kinder", "hund", "velo", "rollstuhl", "rueckerstattung",
        "kontrolle", "busse", "behinderung", "gruppenbillett",
    ):
        if f" {kw} " in t or f"{kw}s " in t:
            tags.append(kw)
    return tags


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    urls = _fetch_sitemap_urls()
    if limit and limit < len(urls):
        urls = urls[:limit]
        logger.info("Limited to first %d URLs.", limit)

    if dry_run:
        logger.info("Sample URLs:")
        for u in urls[:15]:
            logger.info("    %s", u)
        return 0

    cfg = CrawlConfig(
        seeds=urls,
        url_prefix=URL_PREFIX,
        max_pages=len(urls),
        max_depth=0,
        render=False,
    )

    logger.info("Crawl starting — %d URLs.", len(urls))
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    summary = make_and_write(
        category=CATEGORY,
        source_slug=SOURCE_SLUG,
        source_name=SOURCE_NAME,
        authority=AUTHORITY,
        language=LANGUAGE,
        results=results,
        subcategory_for=_subcategory_for,
        tags_for=_tags_for,
        ttl_days=TTL_DAYS,
    )
    logger.info("Total: %s", summary)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ZVV into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap URLs (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
