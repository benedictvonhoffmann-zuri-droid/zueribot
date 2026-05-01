#!/usr/bin/env python3
"""stadt-zuerich.ch ingester — City of Zürich portal.

URL discovery: the site ships a single fat sitemap at
``/de.gsitemap.xml`` (~28k URLs). Most of it is archival noise —
``stadtratsbeschluesse`` (13.7k city-council decisions) and
``amtliche-sammlung`` (2.7k legal gazette entries) alone account for
60% of URLs. We filter with an allowlist of the top-level sections
that contain citizen-facing content.

No Playwright: stadt-zuerich.ch serves real HTML over plain HTTP.
Leaf pages have full content; only landing/hub pages are sparse.

DOM quirks: the site uses a custom design system with web components
(``stzh-heading``, ``stzh-accordion-item``, …). The real page title
lives in ``<meta property="og:title">`` — the ``<h1>`` is literally the
word "Navigation". Sections and accordion items use custom elements
with a ``level`` attribute. We normalise those into standard
``<h1>``/``<h2>``/``<h3>`` before handing off to the shared extractor.

Scope (first pass): DE only. Exclude news, press releases, events,
votings archive, city-council decisions, legal gazette, statistics,
and job postings. Keep: lebenslagen (life situations), department
pages, and topical sections (bildung, gesundheit, mobilitaet,
planen-und-bauen, stadtleben, umwelt-und-energie, service).

Usage:
    python -m scripts.ingest.stadt_zuerich --dry-run --limit 20
    python -m scripts.ingest.stadt_zuerich --limit 100
    python -m scripts.ingest.stadt_zuerich                  # full run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.stadt_zuerich")

SOURCE_NAME = "Stadt Zürich"
SOURCE_SLUG = "stadt_zuerich"
AUTHORITY = "city"
LANGUAGE = "de"
URL_PREFIX = "https://www.stadt-zuerich.ch/de/"
SITEMAP_URL = "https://www.stadt-zuerich.ch/de.gsitemap.xml"
TTL_DAYS = 180


# Top-level URL segment → KB category. Order matters only for
# readability — each URL only matches one path.
CATEGORY_RULES: list[tuple[str, str]] = [
    # life-situation hub — the highest-value section
    ("de/lebenslagen/wohnen", "housing"),
    ("de/lebenslagen/", "admin"),
    # topical sections
    ("de/gesundheit", "health"),
    ("de/mobilitaet", "mobility"),
    ("de/bildung", "education"),
    ("de/stadtleben", "leisure"),
    ("de/planen-und-bauen", "housing"),
    ("de/umwelt-und-energie", "civic"),
    # politics & administration (subset — most of /politik-und-recht/ is excluded)
    ("de/politik-und-verwaltung/behoerden-und-organe", "civic"),
    ("de/politik-und-verwaltung/stadtverwaltung", "civic"),
    ("de/politik-und-verwaltung/strategie-politikfelder", "civic"),
    ("de/politik-und-verwaltung/abstimmen-waehlen", "civic"),
    ("de/politik-und-verwaltung/finanzen", "civic"),
    ("de/politik-und-verwaltung/kommunikation-und-transparenz", "civic"),
    ("de/politik-und-verwaltung/missstaende-melden", "admin"),
    # service pages
    ("de/service", "admin"),
]

# Path prefixes we skip entirely. Covers archival/news/stats/jobs noise
# that made up the bulk of the sitemap.
SKIP_PATH_PREFIXES = (
    "/de/aktuell/",                                  # news, press, events
    "/de/politik-und-verwaltung/politik-und-recht/", # stadtratsbeschluesse + amtliche-sammlung
    "/de/politik-und-verwaltung/statistik-und-daten/",
    "/de/politik-und-verwaltung/arbeiten-bei-der-stadt/",
)

# Sub-paths we skip even when they fall under an allowed section. These
# are archival decision dumps (one page per committee meeting) — same
# noise class as stadtratsbeschluesse but nested deeper in the tree.
SKIP_PATH_SUBSTRINGS = (
    "/schulpflegebeschluesse/",
)


# ── URL discovery ──────────────────────────────────────────────────────────

def _fetch_sitemap_urls(timeout: int = 30) -> list[str]:
    logger.info("Fetching sitemap %s …", SITEMAP_URL)
    resp = requests.get(SITEMAP_URL, timeout=timeout)
    resp.raise_for_status()
    # Regex is ~20x faster than an XML parser on a 5 MB sitemap and
    # tolerates quirks; the schema here is trivial.
    urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    return urls


def _is_allowed(url: str) -> bool:
    if not url.startswith(URL_PREFIX):
        return False
    path = urlparse(url).path
    if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
        return False
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    # Must match at least one category rule.
    return _category_for(url) is not None


def _category_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/")  # drops leading "/"
    for prefix, cat in CATEGORY_RULES:
        if path.startswith(prefix):
            return cat
    return None


def _subcategory_for(url: str) -> Optional[str]:
    cat = _category_for(url)
    if not cat:
        return None
    path = urlparse(url).path.lstrip("/").removeprefix("de/")
    # Use the second path segment (if any) as subcategory suffix,
    # so ``lebenslagen/wohnen`` → ``housing/wohnen``, etc.
    parts = path.split("/")
    if len(parts) >= 2 and parts[1]:
        leaf = parts[1].replace("-", "_").replace(".html", "")
        leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
        if leaf:
            return f"{cat}/{leaf}"
    return None


# ── HTML normalisation ─────────────────────────────────────────────────────

def _normalise_stzh_html(html: bytes) -> bytes:
    """Rewrite stadt-zuerich custom elements into plain HTML.

    - Replace the bogus "Navigation" ``<h1>`` with the real page title
      taken from ``og:title`` (or ``<title>`` minus " | Stadt Zürich").
    - ``<stzh-heading level="N">`` → ``<hN>`` (clamped to h2..h4).
    - ``<stzh-accordion-item heading="X">Y…</stzh-accordion-item>`` →
      ``<h3>X</h3><p>Y…</p>`` so the shared extractor picks them up.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Real title.
    title: Optional[str] = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True).removesuffix(" | Stadt Zürich").strip()

    # Strip the decorative "Navigation" h1 and anything else at h1.
    for h1 in soup.find_all("h1"):  # skipcq: PYL-E1133  (bs4 ResultSet is iterable; pylint can't infer)
        h1.decompose()
    if title and soup.body:
        new_h1 = soup.new_tag("h1")
        new_h1.string = title
        soup.body.insert(0, new_h1)

    # stzh-heading → hN
    for el in soup.find_all("stzh-heading"):  # skipcq: PYL-E1133  (bs4 ResultSet is iterable; pylint can't infer)
        try:
            n = int(el.get("level", "2"))
        except (TypeError, ValueError):
            n = 2
        n = max(2, min(4, n))
        new = soup.new_tag(f"h{n}")
        new.string = el.get_text(" ", strip=True)
        el.replace_with(new)

    # stzh-accordion-item → h3 + body wrapper
    for el in soup.find_all("stzh-accordion-item"):  # skipcq: PYL-E1133  (bs4 ResultSet is iterable; pylint can't infer)
        heading = (el.get("heading") or el.get("label") or "").strip()
        body_text = el.get_text(" ", strip=True)
        if heading and body_text.startswith(heading):
            body_text = body_text[len(heading):].strip()
        wrapper = soup.new_tag("div")
        if heading:
            h = soup.new_tag("h3")
            h.string = heading
            wrapper.append(h)
        if body_text:
            p = soup.new_tag("p")
            p.string = body_text
            wrapper.append(p)
        el.replace_with(wrapper)

    return str(soup).encode("utf-8")


def _normalise_results(results: list) -> list:
    for r in results:
        try:
            r.content = _normalise_stzh_html(r.content)
        except Exception as e:
            logger.warning("normalise failed url=%s err=%s", r.url, e)
    return results


# ── Tags ───────────────────────────────────────────────────────────────────

def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (title + " " + text[:500]).lower()
    for kw in (
        "anmeldung", "zuzug", "umzug", "steuer", "wohnung", "kita",
        "schule", "ausbildung", "velo", "vbz", "abfall", "entsorgung",
        "baubewilligung", "naturalisation", "einburger", "ausweis",
        "hund", "altersheim", "pflege", "sozialhilfe", "notfall",
    ):
        if kw in t:
            tags.append(kw)
    return tags


# ── Runner ─────────────────────────────────────────────────────────────────

def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    all_urls = _fetch_sitemap_urls()
    logger.info("Sitemap: %d URLs total.", len(all_urls))
    kept = [u for u in all_urls if _is_allowed(u)]
    logger.info("Allowlist kept %d URLs.", len(kept))

    # Cap after filtering — sitemap order is semi-random, which spreads
    # the first N across categories rather than starving the tail.
    if limit and limit < len(kept):
        kept = kept[:limit]
        logger.info("Limited to first %d URLs for this run.", limit)

    if dry_run:
        # Summarise by category + print a sampling.
        by_cat: dict[str, int] = {}
        for u in kept:
            cat = _category_for(u) or "?"
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            logger.info("  %-10s %4d", cat, n)
        logger.info("Sample URLs:")
        for u in kept[:15]:
            logger.info("    %s", u)
        return 0

    cfg = CrawlConfig(
        seeds=kept,
        url_prefix=URL_PREFIX,
        max_pages=len(kept),
        max_depth=0,           # sitemap is authoritative — don't BFS
        render=False,          # plain HTTP — no JS needed
    )

    logger.info("Crawl starting — %d URLs, plain HTTP.", len(kept))
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    _normalise_results(results)

    by_cat: dict[str, list] = {}
    for r in results:
        cat = _category_for(r.final_url or r.url)
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
        logger.info("category=%s  %s", cat, summary)
        for k, v in summary.items():
            grand[k] = grand[k] + v

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest stadt-zuerich.ch into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap number of URLs (0 = no cap, default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print URL counts by category + sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
