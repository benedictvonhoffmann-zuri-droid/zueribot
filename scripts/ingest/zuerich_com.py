#!/usr/bin/env python3
"""Zürich Tourism (zuerich.com) ingester.

Fills the food_drink and leisure gaps with Zürich Tourism's visitor
content: restaurants/cafés, nightlife, events, sightseeing, tours.

URL discovery: single sitemap at ``/sitemap.xml`` (~2.6k DE URLs).
We keep only the subsections that carry visitor-facing content and
drop business travel, hotel listings (commercial), newsletters,
neighbourhood stubs.

Each top-level section maps to a KB category:

    essen-trinken       -> food_drink
    events-nachtleben   -> leisure
    sightseeing-aktivitaeten -> leisure
    touren-ausfluege    -> leisure
    kunst-kultur        -> leisure
    besuchen            -> leisure
    informieren-planen  -> leisure  (practical visitor info)

Server-rendered with a real ``<h1>`` — no DOM surgery needed, though
the sitemap does include some stale 404s that the extractor drops via
its title check.

Usage:
    python -m scripts.ingest.zuerich_com --dry-run
    python -m scripts.ingest.zuerich_com --limit 30
    python -m scripts.ingest.zuerich_com
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

logger = logging.getLogger("zuribot.kb.ingest.zuerich_com")

SOURCE_NAME = "Zürich Tourismus"
SOURCE_SLUG = "zuerich_com"
AUTHORITY = "private"
LANGUAGE = "de"
SITEMAP_URL = "https://www.zuerich.com/sitemap.xml"
URL_PREFIX = "https://www.zuerich.com/de/"
TTL_DAYS = 180

# Top-level section -> KB category.
SECTION_TO_CATEGORY: dict[str, str] = {
    "essen-trinken": "food_drink",
    "events-nachtleben": "leisure",
    "sightseeing-aktivitaeten": "leisure",
    "touren-ausfluege": "leisure",
    "kunst-kultur": "leisure",
    "besuchen": "leisure",
    "informieren-planen": "leisure",
}

# Top-level sections we explicitly drop. Business travel,
# commercial hotel listings, and app/newsletter pages don't belong
# in the KB.
DROP_SECTIONS = {
    "business", "unterkunft", "newsletter", "erleben",
    "zuerich-card-city-guide-app", "zuerich-erleben",
}


def _fetch_sitemap_urls(timeout: int = 30) -> list[tuple[str, str]]:
    """Return [(url, category)] for all kept URLs."""
    logger.info("Fetching %s …", SITEMAP_URL)
    resp = requests.get(SITEMAP_URL, timeout=timeout)
    resp.raise_for_status()
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", resp.text)
    kept: list[tuple[str, str]] = []
    for u in urls:
        cat = _classify(u)
        if cat:
            kept.append((u, cat))
    logger.info("sitemap: %d URLs, %d kept", len(urls), len(kept))
    return kept


def _classify(url: str) -> Optional[str]:
    if not url.startswith(URL_PREFIX):
        return None
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    parts = path.split("/", 1)
    if not parts or not parts[0]:
        return None
    section = parts[0]
    if section in DROP_SECTIONS:
        return None
    return SECTION_TO_CATEGORY.get(section)


def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    cat = SECTION_TO_CATEGORY.get(parts[0])
    if not cat:
        return None
    leaf = parts[1].replace("-", "_")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{cat}/{leaf}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:500] + " ").lower()
    for kw in (
        "restaurant", "cafe", "bar", "club", "konzert", "museum",
        "galerie", "see", "fluss", "brunch", "fondue", "raclette",
        "vegan", "vegetarisch", "familie", "kind",
    ):
        if f" {kw} " in t or f"{kw}s " in t:
            tags.append(kw)
    return tags


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    url_cats = _fetch_sitemap_urls()
    # Put rarer categories first so a low --limit still reaches them.
    # zuerich.com's sitemap is leisure-heavy and food_drink URLs sit
    # ~position 1180+; limit=200 in the past truncated to 0 food_drink.
    cat_priority = {"food_drink": 0, "leisure": 1}
    url_cats.sort(key=lambda uc: cat_priority.get(uc[1], 9))
    if limit and limit < len(url_cats):
        url_cats = url_cats[:limit]
        logger.info("Limited to first %d URLs (rarer categories first).", limit)

    if dry_run:
        by_cat: dict[str, int] = {}
        for _, c in url_cats:
            by_cat[c] = by_cat.get(c, 0) + 1
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            logger.info("  %-12s %4d", cat, n)
        return 0

    cat_by_url = {u: c for u, c in url_cats}

    cfg = CrawlConfig(
        seeds=[u for u, _ in url_cats],
        url_prefix=URL_PREFIX,
        max_pages=len(url_cats),
        max_depth=0,
        render=False,
    )

    logger.info("Crawl starting — %d URLs.", len(url_cats))
    with Fetcher(rate_limit_seconds=0.8, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    # Drop zuerich.com's soft-404s (HTTP 200 with 404 h1 content).
    results = [r for r in results if b"Error 404" not in r.content[:20000]]
    logger.info("After soft-404 filter: %d pages.", len(results))

    by_cat: dict[str, list] = {}
    for r in results:
        cat = cat_by_url.get(r.url) or cat_by_url.get(r.final_url)
        if cat is None:
            continue
        by_cat.setdefault(cat, []).append(r)

    grand = {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}
    for cat, res_list in by_cat.items():
        summary = make_and_write(
            category=cat,
            source_slug=SOURCE_SLUG,
            source_name=SOURCE_NAME,
            authority=AUTHORITY,
            language=LANGUAGE,
            results=res_list,
            subcategory_for=_subcategory_for,
            tags_for=_tags_for,
            ttl_days=TTL_DAYS,
        )
        logger.info("category=%s %s", cat, summary)
        for k, v in summary.items():
            grand[k] = grand[k] + v
    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest zuerich.com into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
