#!/usr/bin/env python3
"""ch.ch ingester — federal citizen portal.

Why Playwright: ch.ch is a client-rendered Nuxt 3 SPA. Plain HTTP
yields a ~42 KB empty shell with the text "Suche starten". Only a
real browser (via Playwright) sees the content.

URL discovery: no public sitemap, mega-menu is JS-gated and doesn't
expand on programmatic click. We BFS-crawl from a curated seed list
of top-level topics with depth 3 and a page cap. Coverage is
intentionally imperfect on the first pass — hardening URL-discovery
is a separate follow-up.

Scope: German (`/de/…`) only this first pass. Categories we fill:
admin (most), health (some), mobility (some), education (some).
Page-level ``category`` is chosen from the URL's topic segment.

Usage:
    python -m scripts.ingest.ch_ch                  # default run, ~100 pages
    python -m scripts.ingest.ch_ch --limit 30       # small smoke run
    python -m scripts.ingest.ch_ch --depth 2        # shallower crawl
    python -m scripts.ingest.ch_ch --dry-run        # list discovered URLs, no chunking
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.ch_ch")

SOURCE_NAME = "ch.ch — Bundesportal"
SOURCE_SLUG = "ch_ch"
AUTHORITY = "federal"
LANGUAGE = "de"
URL_PREFIX = "https://www.ch.ch/de/"
TTL_DAYS = 180

# Curated seeds — top-level topics on the DE site.
SEEDS = [
    "https://www.ch.ch/de/",
    "https://www.ch.ch/de/fahrzeuge-und-verkehr",
    "https://www.ch.ch/de/wohnen",
    "https://www.ch.ch/de/arbeit",
    "https://www.ch.ch/de/familie",
    "https://www.ch.ch/de/gesundheit",
    "https://www.ch.ch/de/bildung",
    "https://www.ch.ch/de/migration",
    "https://www.ch.ch/de/sozialversicherungen",
    "https://www.ch.ch/de/steuern-und-finanzen",
    "https://www.ch.ch/de/rechtssystem",
]

# Each URL's first topic segment maps to our KB category.
TOPIC_TO_CATEGORY = {
    "fahrzeuge-und-verkehr": "mobility",
    "wohnen": "housing",
    "arbeit": "admin",
    "familie": "admin",
    "gesundheit": "health",
    "bildung": "education",
    "migration": "admin",
    "sozialversicherungen": "admin",
    "steuern-und-finanzen": "admin",
    "steuern": "admin",
    "rechtssystem": "civic",
    "fluchtlinge": "admin",
}

# Don't follow these — aren't citizen-facing content pages.
SKIP_PATH_PREFIXES = (
    "/de/s/",           # search
    "/de/aktuell",      # news / highlights
    "/de/uber-chch",    # about
    "/de/rechtliches",  # disclaimer
    "/de/voteinfo",
    "/de/volksabstimmung",
)


def _expand_seeds(topic_urls: list[str], timeout_s: int = 30) -> list[str]:
    """Click each sub-category button on each topic page; collect leaf URLs.

    ch.ch's topic landing pages render sub-categories as <button> elements
    (not <a>). Clicking one reveals that sub-category's leaf pages as
    anchors — but navigating away, so we re-goto the topic between clicks.
    Without this, a plain BFS only reaches the 11 seed topics.
    """
    from playwright.sync_api import sync_playwright

    leaves: set[str] = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for topic in topic_urls:
            try:
                page.goto(topic, wait_until="networkidle", timeout=timeout_s * 1000)
                page.wait_for_timeout(600)
                labels = page.evaluate(
                    """Array.from(new Set(
                        Array.from(document.querySelectorAll('main button'))
                          .filter(b => (b.innerText||'').trim() && !b.getAttribute('aria-label'))
                          .map(b => b.innerText.trim())
                    ))"""
                )
                for lbl in labels:
                    try:
                        page.goto(topic, wait_until="networkidle", timeout=timeout_s * 1000)
                        page.wait_for_timeout(400)
                        page.get_by_role("button", name=lbl, exact=True).first.click(timeout=3000)
                        page.wait_for_timeout(500)
                        hs = page.evaluate(
                            """Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))"""
                        )
                        for h in hs or []:
                            if h and h.startswith("/de/") and h.count("/") >= 5:
                                leaves.add(f"https://www.ch.ch{h}".rstrip("/"))
                    except Exception as e:
                        logger.info("expand %s / %r failed: %s", topic, lbl, e)
            except Exception as e:
                logger.info("topic %s failed: %s", topic, e)
        browser.close()
    return sorted(leaves)


def _link_ok(url: str) -> bool:
    path = url.replace("https://www.ch.ch", "", 1)
    if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
        return False
    return True


def _category_for(url: str) -> Optional[str]:
    rest = url.removeprefix(URL_PREFIX).split("/")
    if not rest or not rest[0]:
        return None
    return TOPIC_TO_CATEGORY.get(rest[0])


def _subcategory_for(url: str) -> Optional[str]:
    cat = _category_for(url)
    if not cat:
        return None
    parts = url.removeprefix(URL_PREFIX).split("/")
    if len(parts) >= 2 and parts[1]:
        leaf = parts[1].replace("-", "_")
        leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
        if leaf:
            return f"{cat}/{leaf}"
    return None


def _tags_for(title: str, text: str) -> list[str]:
    # Light heuristic — the reranker cares more about heading_path than tags.
    tags: list[str] = []
    t = (title + " " + text[:500]).lower()
    for kw in ("umzug", "anmeldung", "steuer", "ahv", "iv", "arbeit",
              "krankenkasse", "familie", "schule", "ausbildung",
              "migration", "aufenthalt", "einburger", "vignette", "fuhrausweis"):
        if kw in t:
            tags.append(kw)
    return tags


def run(limit: int, depth: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("Expanding topic seeds via mega-menu clicks…")
    leaves = _expand_seeds(SEEDS)
    logger.info("Discovered %d leaf URLs from %d topics.", len(leaves), len(SEEDS))

    cfg = CrawlConfig(
        seeds=SEEDS + leaves,
        url_prefix=URL_PREFIX,
        max_pages=limit,
        max_depth=depth,
        render=True,
        link_filter=_link_ok,
    )

    logger.info("Crawl starting — max_pages=%d depth=%d", limit, depth)
    with Fetcher(rate_limit_seconds=1.5, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    if dry_run:
        for r in results:
            logger.info("  %s", r.final_url)
        return 0

    # Group by category and write per category.
    by_cat: dict[str, list] = {}
    for r in results:
        cat = _category_for(r.final_url or r.url)
        if cat is None:
            logger.info("no category for url=%s — skipped", r.url)
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
        logger.info("category=%s  %s", cat, summary)
        for k, v in summary.items():
            grand[k] = grand[k] + v

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ch.ch into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=100, help="Max pages to crawl")
    parser.add_argument("--depth", type=int, default=3, help="Max crawl depth")
    parser.add_argument("--dry-run", action="store_true", help="List URLs only")
    args = parser.parse_args()
    return run(limit=args.limit, depth=args.depth, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
