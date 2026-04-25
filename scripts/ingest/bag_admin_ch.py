#!/usr/bin/env python3
"""bag.admin.ch ingester — federal health (Bundesamt für Gesundheit).

Fills the ``health`` gap with citizen-facing federal health content:
disease information, healthy-living guides, vaccination explainers.

URL discovery: sitemap-first. bag.admin.ch publishes a top-level
``sitemap.xml`` that points at sub-sitemaps; we fetch them all and
filter by a curated **allow-list** of section prefixes. A blanket
sitemap pull would yield ~1,800 URLs dominated by press releases,
job postings, and statistical dumps — all noise for the KB.

If the sitemap can't be reached, we fall back to a small BFS crawl
from the section landing pages (``max_depth=3``).

DOM quirk: admin.ch CD/CMS pages sometimes render ``<h1>Navigation</h1>``
above the real article heading. Same fix as easyvote/stadt-zuerich:
strip the chrome and inject ``og:title`` as a fresh ``<h1>`` so the
extractor can find the real title.

Plain HTTP only — bag.admin.ch is server-rendered. Switch to Playwright
only if a future page turns out to be JS-gated.

Usage:
    python -m scripts.ingest.bag_admin_ch --dry-run
    python -m scripts.ingest.bag_admin_ch --limit 30
    python -m scripts.ingest.bag_admin_ch                  # full run
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

logger = logging.getLogger("zuribot.kb.ingest.bag_admin_ch")

SOURCE_NAME = "Bundesamt für Gesundheit (BAG)"
SOURCE_SLUG = "bag_admin_ch"
AUTHORITY = "federal"
CATEGORY = "health"
LANGUAGE = "de"
SITEMAP_URL = "https://www.bag.admin.ch/sitemap.xml"
URL_PREFIX = "https://www.bag.admin.ch/de/"
TTL_DAYS = 365

# bag.admin.ch uses flat /de/<slug> URLs (no nested section paths),
# so prefix filtering doesn't work. We keep slugs whose substring
# matches a citizen-facing health keyword.
KEEP_KEYWORDS = (
    "krankheit", "krankheiten", "impf", "vakzin",
    "gesund-leben", "gesundheitsfoerderung", "praevent",
    "ernaehrung", "bewegung", "sucht", "alkohol", "tabak", "rauchen",
    "schwangerschaft", "geburt", "kind", "jugend", "alter", "alters",
    "psychisch", "psychische-gesundheit",
    "krebs", "diabetes", "demenz", "noso",
    "masern", "grippe", "covid", "corona", "hiv", "hpv",
    "tuberkulose", "kraetze",
    "krankenversicherung", "krankenkasse", "praemie",
    "transplantation", "organspende",
    "notfall", "vergiftung", "strahlenschutz",
    "leichter-sprache",
)

# Hard-reject substrings — admin/expert/comms noise.
SKIP_KEYWORDS = (
    "medienmitteilung", "vernehmlassung", "stellenangebot",
    "abteilung-", "kreisschreiben", "expertengruppe",
    "machbarkeitspruefung", "evaluationsmanagement",
    "kennzahlen", "kommission-", "anhoerung",
    "konsultation", "amtliche-", "pilotprojekt",
    "berichte-ueber", "bevoelkerungsbefragung",
    "bundesgesetz", "verordnung", "teilrevision",
    "agenda", "jahresbericht",
)

# Section landing pages used as BFS fallbacks if no sitemap URLs survive.
SEED_LANDING_PAGES = (
    "https://www.bag.admin.ch/de/uebertragbare-krankheiten",
    "https://www.bag.admin.ch/de/gesund-leben",
)


# ── Sitemap discovery ──────────────────────────────────────────────────────

def _fetch_xml(url: str, timeout: int = 30) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "BuenzliBot/0.1 (+https://buenzli.space/bot)"},
        )
    except requests.RequestException as e:
        logger.warning("sitemap fetch failed url=%s err=%s", url, e)
        return None
    if resp.status_code != 200:
        logger.warning("sitemap status=%s url=%s", resp.status_code, url)
        return None
    return resp.text


def _fetch_sitemap_urls() -> list[str]:
    """Return every <loc> URL found in the sitemap tree, recursively."""
    seen_smaps: set[str] = set()
    queue: list[str] = [SITEMAP_URL]
    all_urls: list[str] = []

    while queue:
        smap = queue.pop(0)
        if smap in seen_smaps:
            continue
        seen_smaps.add(smap)
        text = _fetch_xml(smap)
        if not text:
            continue
        # Sub-sitemaps first
        if "<sitemapindex" in text:
            for m in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text):
                queue.append(m)
            continue
        # Otherwise URL set
        for m in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text):
            all_urls.append(m)
    logger.info("sitemap tree: %d sub-sitemaps, %d URLs total",
                len(seen_smaps), len(all_urls))
    return all_urls


def _is_allowed(url: str) -> bool:
    if not url.startswith(URL_PREFIX):
        return False
    path = urlparse(url).path
    if path.endswith(".pdf"):
        return False
    slug = path.rstrip("/").rsplit("/", 1)[-1].lower()
    if not slug:
        return False
    if any(k in slug for k in SKIP_KEYWORDS):
        return False
    return any(k in slug for k in KEEP_KEYWORDS)


# ── Metadata helpers ───────────────────────────────────────────────────────

def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path
    slug = path.rstrip("/").rsplit("/", 1)[-1].lower().replace(".html", "")
    # Map slug substrings to coarse health subcategories.
    for keyword, leaf in (
        ("impf", "vaccinations"),
        ("krankheit", "diseases"),
        ("masern", "diseases"),
        ("grippe", "diseases"),
        ("covid", "diseases"),
        ("hiv", "diseases"),
        ("hpv", "diseases"),
        ("noso", "diseases"),
        ("kraetze", "diseases"),
        ("tuberkulose", "diseases"),
        ("krebs", "diseases"),
        ("diabetes", "diseases"),
        ("krankenversicherung", "insurance"),
        ("krankenkasse", "insurance"),
        ("praemie", "insurance"),
        ("ernaehrung", "lifestyle"),
        ("bewegung", "lifestyle"),
        ("gesund-leben", "lifestyle"),
        ("sucht", "addiction"),
        ("alkohol", "addiction"),
        ("tabak", "addiction"),
        ("rauchen", "addiction"),
        ("schwangerschaft", "family"),
        ("geburt", "family"),
        ("kind", "family"),
        ("jugend", "family"),
        ("psych", "mental_health"),
        ("transplantation", "transplant"),
        ("organspende", "transplant"),
        ("notfall", "emergency"),
        ("vergiftung", "emergency"),
        ("strahlenschutz", "radiation"),
    ):
        if keyword in slug:
            return f"{CATEGORY}/{leaf}"
    return f"{CATEGORY}/general"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:800] + " ").lower()
    for kw in (
        "impfung", "impfen", "grippe", "covid", "masern", "hpv",
        "hiv", "tuberkulose", "krebs", "diabetes", "ernaehrung",
        "ernährung", "bewegung", "sucht", "alkohol", "tabak",
        "rauchen", "psychische gesundheit", "schwangerschaft",
        "kinder", "alter", "krankenkasse", "praemie", "prämie",
    ):
        if kw in t:
            tag = kw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            tag = tag.replace(" ", "_")
            if tag not in tags:
                tags.append(tag)
    return tags


# ── HTML normalisation ─────────────────────────────────────────────────────

def _normalise_html(html: bytes) -> bytes:
    """Drop admin.ch chrome; inject og:title as <h1> if the real one is missing."""
    soup = BeautifulSoup(html, "html.parser")

    # Strip site chrome that otherwise leaks into <main>.
    for sel in (
        ".mod-navigation", ".mod-breadcrumb", ".mod-footer",
        ".mod-meta-navigation", ".mod-search", ".mod-language-nav",
        ".breadcrumb", ".navigation", ".search-bar",
    ):
        for el in soup.select(sel):
            el.decompose()

    # Drop bogus <h1>Navigation</h1> (or similar) that some admin.ch pages
    # emit above the real article heading.
    for h1 in list(soup.find_all("h1")):
        text = h1.get_text(" ", strip=True).lower()
        if text in {"navigation", "menu", "menü", "suche", "search"}:
            h1.decompose()

    if soup.find("h1"):
        return str(soup).encode("utf-8")

    # No real h1 — use og:title (or <title>) and inject one.
    title: Optional[str] = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        t = soup.title.get_text(strip=True)
        title = t.removesuffix(" | BAG").strip() if t else None

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


# ── Main entry ─────────────────────────────────────────────────────────────

def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sitemap_urls = _fetch_sitemap_urls()
    urls = [u for u in sitemap_urls if _is_allowed(u)]
    logger.info("sitemap kept: %d / %d", len(urls), len(sitemap_urls))

    seeds = urls if urls else list(SEED_LANDING_PAGES)
    use_bfs = not urls
    if use_bfs:
        logger.info("No sitemap URLs survived filter — falling back to BFS crawl.")

    if limit and limit < len(seeds):
        seeds = seeds[:limit]
        logger.info("Limited to first %d URLs.", limit)

    if dry_run:
        logger.info("Sample URLs:")
        for u in seeds[:20]:
            logger.info("    %s", u)
        return 0

    # BFS depth: 0 when we have a curated sitemap-derived list,
    # 3 when we're falling back to landing-page crawling.
    cfg = CrawlConfig(
        seeds=seeds,
        url_prefix=URL_PREFIX,
        max_pages=max(len(seeds), 50) if not use_bfs else 200,
        max_depth=0 if not use_bfs else 3,
        render=False,
        link_filter=_is_allowed if use_bfs else None,
    )

    logger.info("Crawl starting — %d seeds (bfs=%s).", len(seeds), use_bfs)
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
    parser = argparse.ArgumentParser(description="Ingest bag.admin.ch into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap URLs (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
