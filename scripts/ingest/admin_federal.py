#!/usr/bin/env python3
"""Federal admin.ch ingester — three sites, one script.

Covers three Swiss federal offices that publish citizen-facing
explainers and procedures the cantonal/city portals link out to:

    estv.admin.ch  Eidg. Steuerverwaltung           procedure  admin
    sem.admin.ch   Staatssekretariat für Migration  procedure  admin
    bsv.admin.ch   Bundesamt für Sozialversich.     article    admin

URL discovery differs per site:

* estv + bsv use a flat ``/de/<slug>`` URL shape with a working
  ``/sitemap/de.xml`` (~700 / 365 URLs respectively). We keep slugs
  matching a citizen-facing keyword list and reject admin/comms noise.

* sem.admin.ch has no public sitemap. We BFS from a handful of topic
  landing pages under ``/sem/de/home/themen/{aufenthalt,einreise,asyl,
  integration,buergerrecht,ausweise}`` with depth=3.

All three are server-rendered admin.ch deployments; plain HTTP suffices.

Usage:
    python -m scripts.ingest.admin_federal --site estv --limit 10 --dry-run
    python -m scripts.ingest.admin_federal --site sem --limit 50
    python -m scripts.ingest.admin_federal                                 # all three
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.admin_federal")


# ── Per-site profiles ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class SiteProfile:
    slug: str
    name: str
    url_prefix: str
    sitemap_url: Optional[str] = None
    keep_keywords: tuple[str, ...] = ()
    skip_keywords: tuple[str, ...] = ()
    bfs_seeds: tuple[str, ...] = ()
    bfs_max_depth: int = 0
    bfs_max_pages: int = 0


COMMON_SKIP_KW = (
    "medienmitteilung", "vernehmlassung", "stellenangebot",
    "stellen-", "kreisschreiben", "expertengruppe",
    "konsultation", "anhoerung",
    "agenda", "jahresbericht", "geschaeftsbericht",
    "statistik-", "statistiken-",
    "archiv-", "newnsb",
)

PROFILES: dict[str, SiteProfile] = {
    "estv": SiteProfile(
        slug="estv",
        name="Eidgenössische Steuerverwaltung",
        url_prefix="https://www.estv.admin.ch/de/",
        sitemap_url="https://www.estv.admin.ch/sitemap/de.xml",
        keep_keywords=(
            "steuer", "mwst", "mehrwertsteuer", "verrechnungssteuer",
            "stempelabgabe", "tabaksteuer", "biersteuer",
            "quellensteuer", "individualbesteuerung", "ehepaar",
            "abzug", "freibetrag", "tarif", "rueckerstattung",
            "natuerliche-personen", "juristische-personen",
            "selbstaendig", "unternehmen-und-",
            "bundessteuer", "doppelbesteuerung",
        ),
        skip_keywords=COMMON_SKIP_KW + (
            "land-",            # country-by-country DTA pages
            "doppelbesteuerungsabkommen-mit-",
            "mitteilungen-vom",
            "estv-befragungen",
            "tageskurse",
            "rundschreiben",
        ),
    ),
    "bsv": SiteProfile(
        slug="bsv",
        name="Bundesamt für Sozialversicherungen BSV",
        url_prefix="https://www.bsv.admin.ch/de/",
        sitemap_url="https://www.bsv.admin.ch/sitemap/de.xml",
        keep_keywords=(
            "ahv", "alters-und-hinterlassenen", "altersvorsorge",
            "invalidenversicherung", "iv-",
            "ergaenzungsleistung", "el-",
            "familienzulage", "famz",
            "erwerbsersatz", "eo-",
            "mutterschaft", "vaterschaft", "elternschaft",
            "hinterlassenen",
            "bvg", "berufliche-vorsorge", "pensionskasse",
            "saeule", "ueberbrueckungs",
            "fuer-die-aus", "rente",
            "leichter-sprache",
        ),
        skip_keywords=COMMON_SKIP_KW + (
            "ausschreibung",
            "test-",
            "wisier",
            "publikation",
        ),
    ),
    "sem": SiteProfile(
        slug="sem",
        name="Staatssekretariat für Migration SEM",
        url_prefix="https://www.sem.admin.ch/sem/de/",
        bfs_seeds=(
            "https://www.sem.admin.ch/sem/de/home/themen/aufenthalt.html",
            "https://www.sem.admin.ch/sem/de/home/themen/einreise.html",
            "https://www.sem.admin.ch/sem/de/home/themen/asyl.html",
            "https://www.sem.admin.ch/sem/de/home/themen/integration.html",
            "https://www.sem.admin.ch/sem/de/home/themen/buergerrecht.html",
            "https://www.sem.admin.ch/sem/de/home/themen/ausweise.html",
        ),
        bfs_max_depth=3,
        bfs_max_pages=200,
        skip_keywords=COMMON_SKIP_KW + ("/publiservice/", "/statistik/"),
    ),
}

CATEGORY = "admin"
AUTHORITY = "federal"
LANGUAGE = "de"
TTL_DAYS = 365


# ── URL discovery ──────────────────────────────────────────────────────────

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def _fetch_sitemap_urls(profile: SiteProfile, timeout: int = 30) -> list[str]:
    if not profile.sitemap_url:
        return []
    logger.info("[%s] fetching %s …", profile.slug, profile.sitemap_url)
    try:
        resp = requests.get(profile.sitemap_url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("[%s] sitemap fetch failed: %s", profile.slug, e)
        return []
    return _LOC_RE.findall(resp.text)


def _slug_of(url: str) -> str:
    path = urlparse(url).path
    return path.rstrip("/").rsplit("/", 1)[-1].lower().removesuffix(".html")


def _is_allowed_keyword(url: str, profile: SiteProfile) -> bool:
    if not url.startswith(profile.url_prefix):
        return False
    if url.endswith(".pdf"):
        return False
    slug = _slug_of(url)
    if not slug:
        return False
    if any(k in slug for k in profile.skip_keywords):
        return False
    if not profile.keep_keywords:
        return True
    return any(k in slug for k in profile.keep_keywords)


def _is_allowed_path_substring(url: str, profile: SiteProfile) -> bool:
    """For BFS sites: keep anything under url_prefix that doesn't match a skip kw."""
    if not url.startswith(profile.url_prefix):
        return False
    if url.endswith(".pdf"):
        return False
    path = urlparse(url).path.lower()
    if any(s in path for s in profile.skip_keywords):
        return False
    return True


def _subcategory_for(url: str) -> Optional[str]:
    slug = _slug_of(url)
    if not slug:
        return None
    leaf = slug.replace("-", "_")
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    # Cap leaf length so subcategory doesn't get unwieldy.
    leaf = leaf[:40]
    return f"{CATEGORY}/{leaf}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:600] + " ").lower()
    for kw in (
        "steuer", "mehrwertsteuer", "verrechnungssteuer", "ahv", "iv",
        "ergaenzungsleistung", "familienzulage", "pensionskasse", "bvg",
        "aufenthalt", "bewilligung", "asyl", "einreise", "integration",
        "buergerrecht", "einbuergerung", "ausweis", "visum",
    ):
        if kw in t:
            tags.append(kw)
    return tags


# ── Runner ─────────────────────────────────────────────────────────────────

def _run_site(profile: SiteProfile, limit: int, dry_run: bool) -> dict:
    use_bfs = profile.sitemap_url is None

    if use_bfs:
        seeds = list(profile.bfs_seeds)
        max_pages = profile.bfs_max_pages
        max_depth = profile.bfs_max_depth
        logger.info("[%s] BFS mode — %d seeds, max_depth=%d, max_pages=%d",
                    profile.slug, len(seeds), max_depth, max_pages)
        def link_filter(u):
            return _is_allowed_path_substring(u, profile)
    else:
        all_urls = _fetch_sitemap_urls(profile)
        logger.info("[%s] sitemap: %d URLs total.", profile.slug, len(all_urls))
        seeds = [u for u in all_urls if _is_allowed_keyword(u, profile)]
        logger.info("[%s] keyword filter kept %d URLs.", profile.slug, len(seeds))
        max_pages = max(len(seeds), 50)
        max_depth = 0
        link_filter = None

    if limit and limit < len(seeds):
        seeds = seeds[:limit]
        logger.info("[%s] limited to first %d URLs.", profile.slug, limit)
        if not use_bfs:
            max_pages = len(seeds)

    if dry_run:
        for u in seeds[:15]:
            logger.info("    %s", u)
        return {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    if not seeds:
        logger.warning("[%s] nothing to crawl.", profile.slug)
        return {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    cfg = CrawlConfig(
        seeds=seeds,
        url_prefix=profile.url_prefix,
        max_pages=max_pages,
        max_depth=max_depth,
        render=False,
        link_filter=link_filter,
    )

    logger.info("[%s] crawl starting — %d seeds.", profile.slug, len(seeds))
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("[%s] crawl done. %d pages fetched.", profile.slug, len(results))

    summary = make_and_write(
        category=CATEGORY,
        source_slug=profile.slug,
        source_name=profile.name,
        authority=AUTHORITY,
        language=LANGUAGE,
        results=results,
        subcategory_for=_subcategory_for,
        tags_for=_tags_for,
        ttl_days=TTL_DAYS,
    )
    logger.info("[%s] %s", profile.slug, summary)
    return summary


def run(site: str, limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    targets = list(PROFILES.values()) if site == "all" else [PROFILES[site]]

    grand = {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}
    for profile in targets:
        s = _run_site(profile, limit=limit, dry_run=dry_run)
        for k, v in s.items():
            grand[k] = grand[k] + v
    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest federal admin.ch sites (estv/sem/bsv) into Phase 1 .jsonl")
    parser.add_argument("--site", choices=["estv", "sem", "bsv", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Cap URLs per site (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true", help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(site=args.site, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
