#!/usr/bin/env python3
"""easyvote ingester — civic explainers (voting, elections, how-to).

Fills the civic gap with plain-language Swiss voting content: how to
vote, how elections work, what a referendum is. Run by the Dachverband
Schweizer Jugendparlamente — authority="community".

URL discovery: single sitemap at ``/de/sitemap.xml``. We keep current
ballot explainers + ``/wissen`` + ``/wahlen`` and drop the archive
(historical ballots) plus internal/test paths.

DOM quirk: no real ``<h1>`` — the page title lives in ``<meta
og:title>``. Same treatment as stadt-zuerich.ch and zh.ch.

Usage:
    python -m scripts.ingest.easyvote --dry-run
    python -m scripts.ingest.easyvote --limit 30
    python -m scripts.ingest.easyvote                   # full run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.easyvote")

SOURCE_NAME = "easyvote"
SOURCE_SLUG = "easyvote"
AUTHORITY = "community"
CATEGORY = "civic"
LANGUAGE = "de"
SITEMAP_URL = "https://www.easyvote.ch/de/sitemap.xml"
URL_PREFIX = "https://www.easyvote.ch/de/"
TTL_DAYS = 365

# Only these top-level sections carry KB-worthy evergreen civic content.
ALLOW_PREFIXES = (
    "https://www.easyvote.ch/de/wissen",
    "https://www.easyvote.ch/de/wahlen",
    "https://www.easyvote.ch/de/abstimmungen",
)

SKIP_PATH_SUBSTRINGS = (
    "/archiv",            # past-ballot explainers — dated, huge volume
    "/aktuelles",         # news
    "/rm-test",           # internal test material
    "/projekt-",          # internal project pages
    "/abbestellen",
    "/sprache",
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
    if not any(url.startswith(p) for p in ALLOW_PREFIXES):
        return False
    path = urlparse(url).path
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    return True


def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    parts = path.split("/")
    if not parts or not parts[0]:
        return None
    leaf = parts[0].replace("-", "_")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:500] + " ").lower()
    for kw in (
        "abstimmung", "wahl", "initiative", "referendum", "bundesrat",
        "parlament", "nationalrat", "staenderat", "stimmrecht",
        "brief", "urne", "proporz", "majorz",
    ):
        if f" {kw} " in t or f"{kw}en " in t:
            tags.append(kw)
    return tags


def _normalise_html(html: bytes) -> bytes:
    """Drop the mobile menu drawer (leaks into <main>) and inject og:title as <h1>."""
    soup = BeautifulSoup(html, "html.parser")

    # The mobile menu drawer is rendered inside <main> and its ``.navi``
    # <ul>s look like paragraphs to the extractor. Drop them here.
    for sel in (".menu-drawer", ".siteheader-main-navi", ".sitefooter-navi",
                "ul.navi", ".breadcrumb"):
        for el in soup.select(sel):
            el.decompose()

    if soup.find("h1"):
        # Some pages have a real h1; leave those alone.
        return str(soup).encode("utf-8")

    title: Optional[str] = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True).removesuffix(" | easyvote").strip()

    if title and soup.body:
        new_h1 = soup.new_tag("h1")
        new_h1.string = title
        soup.body.insert(0, new_h1)
    return str(soup).encode("utf-8")


def _normalise_results(results: list) -> list:
    for r in results:
        try:
            r.content = _normalise_html(r.content)
        except Exception as e:
            logger.warning("normalise failed url=%s err=%s", r.url, e)
    return results


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

    _normalise_results(results)

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
    parser = argparse.ArgumentParser(description="Ingest easyvote into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap URLs (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
