#!/usr/bin/env python3
"""Universities ingester — UZH, ETH, ZHAW, PHZH.

Multi-domain ingester for the four big Zürich tertiary institutions.
Each domain becomes its own ``source_slug`` (uzh, ethz, zhaw, phzh)
under ``data/chunks/education/{slug}/``. Category is ``education``,
authority ``community`` (universities are autonomous public bodies,
not federal/cantonal admin in the trust-weighting sense), language
``de`` for the smoke run.

Focus: prospective-students content — how to apply, study programmes
overview, tuition, language requirements. We BFS from a small set of
"Studium" / "Studies" hub URLs per site and stay inside those trees.

Usage:
    python -m scripts.ingest.unis --site uzh --limit 10 --dry-run
    python -m scripts.ingest.unis --site uzh --limit 30
    python -m scripts.ingest.unis --site all
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.unis")

CATEGORY = "education"
AUTHORITY = "community"
LANGUAGE = "de"
TTL_DAYS = 365


@dataclass
class SiteConfig:
    slug: str
    name: str
    url_prefix: str
    seeds: list[str]
    keep_substrings: tuple[str, ...]
    skip_substrings: tuple[str, ...] = field(default_factory=tuple)


SITES: dict[str, SiteConfig] = {
    "uzh": SiteConfig(
        slug="uzh",
        name="Universität Zürich",
        url_prefix="https://www.uzh.ch/de/",
        seeds=[
            "https://www.uzh.ch/de/studies.html",
            "https://www.uzh.ch/de/studies/application.html",
            "https://www.uzh.ch/de/studies/degrees.html",
            "https://www.uzh.ch/de/studies/firstsemester.html",
            "https://www.uzh.ch/de/studies/financial.html",
        ],
        keep_substrings=("/studies",),
        skip_substrings=("/news", "/events", "/media", "/jobs", "/alumni"),
    ),
    "ethz": SiteConfig(
        slug="ethz",
        name="ETH Zürich",
        url_prefix="https://ethz.ch/de/studium",
        seeds=[
            "https://ethz.ch/de/studium.html",
            "https://ethz.ch/de/studium/bachelor.html",
            "https://ethz.ch/de/studium/master.html",
            "https://ethz.ch/de/studium/bewerbung.html",
            "https://ethz.ch/de/studium/finanzielles.html",
        ],
        keep_substrings=("/studium",),
        skip_substrings=("/news", "/aktuell", "/jobs", "/medien", "/events"),
    ),
    "zhaw": SiteConfig(
        slug="zhaw",
        name="Zürcher Hochschule für Angewandte Wissenschaften",
        url_prefix="https://www.zhaw.ch/de/studium",
        seeds=[
            "https://www.zhaw.ch/de/studium/",
            "https://www.zhaw.ch/de/studium/bachelor/",
            "https://www.zhaw.ch/de/studium/master/",
            "https://www.zhaw.ch/de/studium/bewerbung-zulassung/",
            "https://www.zhaw.ch/de/studium/studienfinanzierung/",
        ],
        keep_substrings=("/studium",),
        skip_substrings=("/news", "/medien", "/jobs", "/events", "/aktuell"),
    ),
    # phzh.ch is a SPA with no anchor links and no sitemap.xml — even
    # rendered fetches return 0 internal navigable links. Dropped until
    # we have a click-simulation crawler or a curated URL list.
}


def _link_filter_for(site: SiteConfig) -> Callable[[str], bool]:
    keep = tuple(s.lower() for s in site.keep_substrings)
    skip = tuple(s.lower() for s in site.skip_substrings)

    def f(url: str) -> bool:
        path = urlparse(url).path.lower()
        if any(s in path for s in skip):
            return False
        return any(k in path for k in keep)
    return f


def _subcategory_for(url: str) -> Optional[str]:
    path = urlparse(url).path.lstrip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    leaf = parts[-1].replace(".html", "").replace("-", "_").lower()
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf[:40]}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:800] + " ").lower()
    for kw in (
        "bachelor", "master", "doktorat", "phd", "bewerbung", "zulassung",
        "anmeldung", "studiengang", "studium", "ects", "semester",
        "matura", "stipendium", "studiengeb", "tuition", "deutsch",
        "englisch", "sprachnachweis",
    ):
        if kw in t:
            tags.append(kw)
    return sorted(set(tags))


def _run_site(site: SiteConfig, *, max_pages: int, dry_run: bool) -> dict:
    if dry_run:
        logger.info("[%s] dry-run: %d seeds, max_pages=%d, prefix=%s",
                    site.slug, len(site.seeds), max_pages, site.url_prefix)
        for s in site.seeds:
            logger.info("    %s", s)
        return {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    cfg = CrawlConfig(
        seeds=site.seeds,
        url_prefix=site.url_prefix,
        max_pages=max_pages,
        max_depth=3,
        render=False,
        link_filter=_link_filter_for(site),
    )
    logger.info("[%s] crawl starting — max %d pages.", site.slug, max_pages)
    with Fetcher(rate_limit_seconds=1.2, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("[%s] crawl done. %d pages fetched.", site.slug, len(results))

    summary = make_and_write(
        category=CATEGORY,
        source_slug=site.slug,
        source_name=site.name,
        authority=AUTHORITY,
        language=LANGUAGE,
        results=results,
        subcategory_for=_subcategory_for,
        tags_for=_tags_for,
        ttl_days=TTL_DAYS,
    )
    logger.info("[%s] %s", site.slug, summary)
    return summary


def run(site_arg: str, limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if site_arg == "all":
        targets = list(SITES.values())
    else:
        if site_arg not in SITES:
            logger.error("Unknown site '%s'. Choose from: %s, all",
                         site_arg, ", ".join(SITES.keys()))
            return 2
        targets = [SITES[site_arg]]

    max_pages = limit if limit else 150
    grand = {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}
    for site in targets:
        s = _run_site(site, max_pages=max_pages, dry_run=dry_run)
        for k, v in s.items():
            grand[k] += v

    logger.info("Grand total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest UZH/ETH/ZHAW/PHZH into Phase 1 .jsonl")
    parser.add_argument("--site", choices=["uzh", "ethz", "zhaw", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0,
                        help="Per-site URL cap (0 = default 150).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(site_arg=args.site, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
