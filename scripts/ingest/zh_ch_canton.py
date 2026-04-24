#!/usr/bin/env python3
"""zh.ch ingester — Canton of Zürich portal.

Fills the cantonal authority gap. Covers service areas that are
canton-level (driver's licences, cantonal taxes, migration,
cantonal schools, …) and the directorates.

URL discovery: zh.ch publishes a per-topic sitemap index. We pull
twelve topic sitemaps — one per citizen-facing subject — and merge.
Directorate sitemaps (staatskanzlei, baudirektion, …) are skipped
because their content largely overlaps the topic sitemaps, and their
non-overlap is internal/operational. News, legal gazette, and
Regierungsrat-decision archives are excluded entirely.

DOM quirk: like stadt-zuerich.ch, zh.ch's ``<h1>`` is literally
"Navigation" — the real page title lives in ``<meta og:title>``.
Unlike stadt-zuerich, zh.ch uses plain HTML (no custom web
components), so section extraction via ``<h2>``/``<h3>`` works out
of the box.

No Playwright — pages are server-rendered.

Usage:
    python -m scripts.ingest.zh_ch_canton --dry-run
    python -m scripts.ingest.zh_ch_canton --limit 50
    python -m scripts.ingest.zh_ch_canton                 # full run
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

logger = logging.getLogger("zuribot.kb.ingest.zh_ch_canton")

SOURCE_NAME = "Kanton Zürich"
SOURCE_SLUG = "zh_ch_canton"
AUTHORITY = "cantonal"
LANGUAGE = "de"
URL_PREFIX = "https://www.zh.ch/de/"
TTL_DAYS = 180


# Topic sitemap → KB category. Each topic sitemap lives at
# https://www.zh.ch/de/<topic>.zhweb-sitemap.xml.
TOPIC_SITEMAPS: list[tuple[str, str]] = [
    ("mobilitaet", "mobility"),
    ("planen-bauen", "housing"),
    ("steuern-finanzen", "admin"),
    ("wirtschaft-arbeit", "admin"),
    ("sport-kultur", "leisure"),
    ("bildung", "education"),
    ("soziales", "admin"),
    ("familie", "admin"),
    ("gesundheit", "health"),
    ("umwelt-tiere", "civic"),
    ("migration-integration", "admin"),
    ("sicherheit-justiz", "emergency"),
]

# Path substrings we exclude even when they're in an allowed topic —
# archival or operational content that doesn't belong in the KB.
SKIP_PATH_SUBSTRINGS = (
    "/medienmitteilungen/",
    "/mitteilungen/",
    "/news-uebersicht/",
    "/arbeiten-beim-kanton/",
    "/gesetzessammlung/",              # handled separately as law source
    "/beschluesse-des-regierungsrates/",
)


# ── URL discovery ──────────────────────────────────────────────────────────

def _fetch_topic_urls(timeout: int = 30) -> list[tuple[str, str]]:
    """Return [(url, category), …] across all topic sitemaps, de-duplicated."""
    seen: dict[str, str] = {}
    for topic, cat in TOPIC_SITEMAPS:
        url = f"https://www.zh.ch/de/{topic}.zhweb-sitemap.xml"
        logger.info("Fetching %s …", url)
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("skip sitemap %s: %s", url, e)
            continue
        urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", resp.text)
        new = 0
        for u in urls:
            if not _is_allowed(u):
                continue
            if u in seen:
                continue
            seen[u] = cat
            new += 1
        logger.info("  %s: %d kept (%d new)", topic, len(urls), new)
    return list(seen.items())


def _is_allowed(url: str) -> bool:
    if not url.startswith(URL_PREFIX):
        return False
    path = urlparse(url).path
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    # Strip obvious noise: the sitemap includes top-level .html index
    # pages like /de/mobilitaet.html with minimal content. Keep only
    # pages one level below a topic.
    if path.count("/") < 3:
        return False
    return True


_TOPIC_TO_CAT = dict(TOPIC_SITEMAPS)


def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    cat = _TOPIC_TO_CAT.get(parts[0])
    if not cat:
        return None
    leaf = parts[1].replace("-", "_").replace(".html", "")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{cat}/{leaf}"


# ── HTML normalisation ─────────────────────────────────────────────────────

def _normalise_html(html: bytes) -> bytes:
    """Replace the bogus "Navigation" <h1> with the real og:title."""
    soup = BeautifulSoup(html, "html.parser")

    title: Optional[str] = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True).removesuffix(" | Kanton Zürich").strip()

    for h1 in soup.find_all("h1"):
        h1.decompose()
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


# ── Tags ───────────────────────────────────────────────────────────────────

def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:500] + " ").lower()
    for kw in (
        "fuhrerausweis", "fuehrerausweis", "motorfahrzeug", "vignette",
        "steuer", "erbschaft", "gesuch", "bewilligung", "lernfahr",
        "krankenkasse", "ahv", "iv", "unfall", "kesb", "migration",
        "asyl", "einbuergerung", "schule", "kantonsschule",
    ):
        if f" {kw} " in t or f"{kw}en " in t:
            tags.append(kw)
    return tags


# ── Runner ─────────────────────────────────────────────────────────────────

def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    url_cats = _fetch_topic_urls()
    logger.info("Topic sitemaps: %d unique URLs kept.", len(url_cats))

    if limit and limit < len(url_cats):
        url_cats = url_cats[:limit]
        logger.info("Limited to first %d URLs.", limit)

    if dry_run:
        by_cat: dict[str, int] = {}
        for _, cat in url_cats:
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            logger.info("  %-10s %4d", cat, n)
        logger.info("Sample URLs:")
        for u, _ in url_cats[:10]:
            logger.info("    %s", u)
        return 0

    # Map from URL → category for routing after fetch.
    cat_by_url = {u: c for u, c in url_cats}

    cfg = CrawlConfig(
        seeds=[u for u, _ in url_cats],
        url_prefix=URL_PREFIX,
        max_pages=len(url_cats),
        max_depth=0,
        render=False,
    )

    logger.info("Crawl starting — %d URLs, plain HTTP.", len(url_cats))
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    _normalise_results(results)

    by_cat: dict[str, list] = {}
    for r in results:
        cat = cat_by_url.get(r.url) or cat_by_url.get(r.final_url)
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
    parser = argparse.ArgumentParser(description="Ingest zh.ch (canton) into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap number of URLs (0 = no cap, default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print URL counts by category + sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
