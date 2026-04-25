#!/usr/bin/env python3
"""Housing-association ingester — Mieterverband + HEV Schweiz.

Two advocacy associations explaining tenant- and landlord-rights in
plain German: Mietrecht primers, Nebenkosten, Kündigung, Mietzinser-
höhung. Both `authority="community"`, both `housing` category.

URL discovery: BFS from a curated seed list per site, restricted to
each site's tenant-rights / landlord-rights explainer trees. We do
not crawl the news/press/member sections (login walls, dated content).

Mieterverband cap: per spec §11.2, MV must not exceed ~15% of total
`housing` chunks. We enforce this at the ingester level by capping
the MV crawl at a small URL budget, lower than HEV's. The default
budget for MV is roughly half of HEV; tune via ``--mv-cap``.

Usage:
    python -m scripts.ingest.housing_assoc --dry-run --limit 10
    python -m scripts.ingest.housing_assoc --limit 30
    python -m scripts.ingest.housing_assoc                       # full run
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional
from urllib.parse import urlparse

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.housing_assoc")

CATEGORY = "housing"
AUTHORITY = "community"
LANGUAGE = "de"
TTL_DAYS = 365


# ── Mieterverband ──────────────────────────────────────────────────────────
MV_SOURCE_NAME = "Mieterinnen- und Mieterverband"
MV_SOURCE_SLUG = "mieterverband"
MV_URL_PREFIX = "https://www.mieterverband.ch/mv/"
MV_SEEDS = [
    # Top-level tenant-rights explainer hubs.
    "https://www.mieterverband.ch/mv/mietrecht-beratung/ratgeber-mietrecht.html",
    "https://www.mieterverband.ch/mv/mietrecht-beratung/haeufige-fragen.html",
    "https://www.mieterverband.ch/mv/mietrecht-beratung.html",
    "https://www.mieterverband.ch/mv/mietrecht-beratung/musterbriefe.html",
]
# Skip news / member / login / press / shop noise.
MV_SKIP = (
    "/aktuell/",
    "/news/",
    "/medien/",
    "/medienmitteilungen/",
    "/shop",
    "/login",
    "/mitgliedschaft",
    "/spenden",
    "/kontakt",
    "/ueber-uns",
    "/jobs",
    "/agenda",
    "/veranstaltungen",
    "/sektionen",
    "/kampagnen",
)


def _mv_link_filter(url: str) -> bool:
    path = urlparse(url).path.lower()
    if any(s in path for s in MV_SKIP):
        return False
    # Stay inside the substantive section trees.
    keep = (
        "/mietrecht-beratung",
        "/ratgeber",
        "/musterbriefe",
        "/haeufige-fragen",
    )
    return any(k in path for k in keep)


def _mv_subcategory(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    leaf = parts[-1].replace(".html", "").replace("-", "_")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf[:40]}"


# ── HEV Schweiz ────────────────────────────────────────────────────────────
HEV_SOURCE_NAME = "Hauseigentümerverband Schweiz"
HEV_SOURCE_SLUG = "hev_schweiz"
HEV_URL_PREFIX = "https://www.hev-schweiz.ch/"
HEV_SEEDS = [
    # Landlord-side explainer hubs ("Vermieten", "Wohnen", "Recht & Steuern").
    "https://www.hev-schweiz.ch/vermieten",
    "https://www.hev-schweiz.ch/vermieten/mietrecht",
    "https://www.hev-schweiz.ch/vermieten/nebenkosten",
    "https://www.hev-schweiz.ch/vermieten/mietzins",
    "https://www.hev-schweiz.ch/vermieten/kuendigung",
    "https://www.hev-schweiz.ch/wohnen",
    "https://www.hev-schweiz.ch/recht-steuern",
    "https://www.hev-schweiz.ch/bauen-modernisieren",
]
HEV_SKIP = (
    "/aktuell",
    "/news",
    "/medien",
    "/presse",
    "/shop",
    "/login",
    "/mitglied",
    "/sektion",
    "/jobs",
    "/agenda",
    "/veranstaltung",
    "/kontakt",
    "/ueber-uns",
    "/spenden",
    "/abstimm",  # campaign pages
    "/kampagn",
)


def _hev_link_filter(url: str) -> bool:
    path = urlparse(url).path.lower()
    if any(s in path for s in HEV_SKIP):
        return False
    keep = (
        "/vermieten",
        "/wohnen",
        "/recht-steuern",
        "/bauen-modernisieren",
        "/ratgeber",
    )
    return any(k in path for k in keep)


def _hev_subcategory(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    leaf = parts[-1].replace(".html", "").replace("-", "_")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf[:40]}"


# ── Tags (shared) ──────────────────────────────────────────────────────────
def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:800] + " ").lower()
    for kw in (
        "miete", "mietrecht", "mietvertrag", "mietzins", "mietzinserhoehung",
        "nebenkosten", "kuendigung", "kündigung", "untermiete", "kaution",
        "mängel", "maengel", "schlichtung", "vermieter", "mieter", "wohnung",
        "hauseigent", "stockwerkeigentum", "wohneigentum",
    ):
        if kw in t:
            tags.append(kw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))
    return sorted(set(tags))


# ── Runner ─────────────────────────────────────────────────────────────────
def _run_site(
    *, source_slug: str, source_name: str, url_prefix: str, seeds: list[str],
    link_filter, subcategory_for, max_pages: int, dry_run: bool,
) -> dict:
    if dry_run:
        logger.info("[%s] dry-run: %d seeds, max_pages=%d", source_slug, len(seeds), max_pages)
        for s in seeds:
            logger.info("    %s", s)
        return {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    cfg = CrawlConfig(
        seeds=seeds,
        url_prefix=url_prefix,
        max_pages=max_pages,
        max_depth=3,
        render=False,
        link_filter=link_filter,
    )
    logger.info("[%s] crawl starting — max %d pages.", source_slug, max_pages)
    with Fetcher(rate_limit_seconds=1.2, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("[%s] crawl done. %d pages fetched.", source_slug, len(results))

    summary = make_and_write(
        category=CATEGORY,
        source_slug=source_slug,
        source_name=source_name,
        authority=AUTHORITY,
        language=LANGUAGE,
        results=results,
        subcategory_for=subcategory_for,
        tags_for=_tags_for,
        ttl_days=TTL_DAYS,
    )
    logger.info("[%s] %s", source_slug, summary)
    return summary


def run(limit: int, mv_cap: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # MV is capped lower than HEV per §11.2 (~15% rule).
    # When --limit is set, treat it as the HEV budget; MV gets min(limit, mv_cap).
    if limit:
        hev_cap = limit
        mv_budget = min(limit, mv_cap)
    else:
        hev_cap = 200
        mv_budget = mv_cap

    grand = {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    s = _run_site(
        source_slug=HEV_SOURCE_SLUG,
        source_name=HEV_SOURCE_NAME,
        url_prefix=HEV_URL_PREFIX,
        seeds=HEV_SEEDS,
        link_filter=_hev_link_filter,
        subcategory_for=_hev_subcategory,
        max_pages=hev_cap,
        dry_run=dry_run,
    )
    for k, v in s.items():
        grand[k] += v

    s = _run_site(
        source_slug=MV_SOURCE_SLUG,
        source_name=MV_SOURCE_NAME,
        url_prefix=MV_URL_PREFIX,
        seeds=MV_SEEDS,
        link_filter=_mv_link_filter,
        subcategory_for=_mv_subcategory,
        max_pages=mv_budget,
        dry_run=dry_run,
    )
    for k, v in s.items():
        grand[k] += v

    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Mieterverband + HEV into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Per-site URL cap for HEV (MV stays capped at --mv-cap or limit, whichever is smaller). 0 = defaults.")
    parser.add_argument("--mv-cap", type=int, default=30,
                        help="Hard cap on Mieterverband URLs (default 30) — enforces the §11.2 ~15%% rule.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(limit=args.limit, mv_cap=args.mv_cap, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
