#!/usr/bin/env python3
"""Quartiervereine ingester — neighborhood associations of the City of Zürich.

Each Quartier (and the broader Kreis around it) has a volunteer-run
neighborhood association. Their websites carry hyperlocal background
that's not on the official portals: Quartier history, recurring events,
local committees, neighbour-relations, traditions. Useful as a
``neighborhoods`` layer for Bünzli's voice and for "where do I…"
questions that don't have an obvious official answer.

Discovery: the umbrella `quartierverein.ch` lists each association with
a link to its website. The list below is curated from that page (April
2026) — ~25 sites, each on its own domain. Many are WordPress, some are
older custom sites.

Per Quartierverein gets its own ``source_slug`` (e.g. ``qv_affoltern``)
under ``data/chunks/neighborhoods/{slug}/`` so retrieval can attribute
content to the right neighbourhood.

Quality concern: these are volunteer sites. Content quality varies
wildly. Conservative caps per site (default 12 pages, depth 2) plus the
existing 300-char content threshold in ``_base.py`` filters out thin
event-list pages.

Usage:
    python -m scripts.ingest.quartiervereine --dry-run
    python -m scripts.ingest.quartiervereine --site qv_affoltern --limit 5
    python -m scripts.ingest.quartiervereine --limit 12
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.quartiervereine")

CATEGORY = "neighborhoods"
AUTHORITY = "community"
LANGUAGE = "de"
TTL_DAYS = 365


@dataclass
class SiteConfig:
    slug: str            # e.g. qv_affoltern  (becomes source_slug)
    name: str            # display name (becomes source_name)
    quartier: str        # primary Quartier covered
    kreis: str           # Stadtkreis number, as a string ("11", "4-5")
    url_prefix: str      # https://www.example.ch  (used for BFS prefix match)
    seed: str            # entry URL for the BFS


# Curated 2026-04-25 from https://www.quartierverein.ch/vereine/.
# Ordered roughly by Kreis (1 → 12). Each entry covers one or more
# Quartiere; the umbrella site treats each Verein as one entry, so we
# do the same.
SITES: list[SiteConfig] = [
    SiteConfig("qv_zuerich1",   "Quartierverein Zürich 1 rechts der Limmat", "Altstadt-Hochschulen", "1",
               "https://www.quartierverein-zuerich1.ch", "https://www.quartierverein-zuerich1.ch/"),
    SiteConfig("qv_enge",       "Quartierverein Enge",                       "Enge",                 "2",
               "https://www.enge.ch", "https://www.enge.ch/"),
    SiteConfig("qv_leimbach",   "Quartierverein Leimbach",                   "Leimbach",             "2",
               "https://www.zuerich-leimbach.ch", "https://www.zuerich-leimbach.ch/"),
    SiteConfig("qv_wollishofen","Quartierverein Wollishofen",                "Wollishofen",          "2",
               "https://www.wollishofen-zh.ch", "https://www.wollishofen-zh.ch/"),
    SiteConfig("qv_wiedikon",   "Quartierverein Wiedikon",                   "Alt-Wiedikon/Friesenberg/Sihlfeld", "3",
               "https://www.quartierverein-wiedikon.ch", "https://www.quartierverein-wiedikon.ch/"),
    SiteConfig("qv_triemli",    "Quartierverein Friesenberg-Triemli",        "Friesenberg/Triemli",  "3",
               "https://www.quartierverein-triemli.ch", "https://www.quartierverein-triemli.ch/"),
    SiteConfig("qv_aussersihl", "Quartierverein Aussersihl Kreis 4",         "Aussersihl",           "4",
               "https://www.8004.ch", "https://www.8004.ch/"),
    # Quartierverein Kreis 5 (Industriequartier) had domains qv5.ch /
    # chreis5.ch — both now redirect to chreis5.info casino-spam. Verein
    # appears defunct as of 2026-04-25; re-add if a clean domain reappears.
    SiteConfig("qv_unterstrass","Quartierverein Unterstrass",                "Unterstrass",          "6",
               "https://www.unterstrass.ch", "https://www.unterstrass.ch/"),
    SiteConfig("qv_oberstrass", "Quartierverein Oberstrass",                 "Oberstrass",           "6",
               "https://www.qvo.ch", "https://www.qvo.ch/"),
    SiteConfig("qv_fluntern",   "Quartierverein Fluntern",                   "Fluntern",             "7",
               "https://www.zuerich-fluntern.ch", "https://www.zuerich-fluntern.ch/"),
    SiteConfig("qv_hottingen",  "Quartierverein Hottingen",                  "Hottingen",            "7",
               "https://www.hottingen.ch", "https://www.hottingen.ch/"),
    SiteConfig("qv_hirslanden", "Quartierverein Hirslanden",                 "Hirslanden",           "7",
               "https://www.qv-hirslanden.ch", "https://www.qv-hirslanden.ch/"),
    SiteConfig("qv_witikon",    "Quartierverein Witikon",                    "Witikon",              "7",
               "https://www.zuerich-witikon.ch", "https://www.zuerich-witikon.ch/"),
    SiteConfig("qv_riesbach",   "Quartierverein Riesbach",                   "Seefeld/Mühlebach",    "8",
               "https://www.8008.ch", "https://www.8008.ch/"),
    # rqv.ch (sister Riesbach association) was 500-erroring on 2026-04-25;
    # Riesbach is already covered by 8008.ch above. Re-add if rqv.ch returns.
    SiteConfig("qv_albisrieden","Quartierverein Albisrieden",                "Albisrieden",          "9",
               "https://www.zuerich-albisrieden.ch", "https://www.zuerich-albisrieden.ch/"),
    SiteConfig("qv_altstetten", "Quartierverein Altstetten",                 "Altstetten",           "9",
               "https://www.quartierverein-altstetten.ch", "https://www.quartierverein-altstetten.ch/"),
    SiteConfig("qv_gruenau",    "Quartierverein Grünau",                     "Grünau",               "9",
               "https://www.gruenau.ch", "https://www.gruenau.ch/"),
    SiteConfig("qv_hoengg",     "Quartierverein Höngg",                      "Höngg",                "10",
               "https://www.zuerich-hoengg.ch", "https://www.zuerich-hoengg.ch/"),
    SiteConfig("qv_wipkingen",  "Quartierverein Wipkingen",                  "Wipkingen",            "10",
               "https://www.wipkingen.net", "https://www.wipkingen.net/"),
    SiteConfig("qv_affoltern",  "Quartierverein Zürich-Affoltern",           "Affoltern",            "11",
               "https://www.qvaffoltern.ch", "https://www.qvaffoltern.ch/"),
    SiteConfig("qv_oerlikon",   "Quartierverein Oerlikon",                   "Oerlikon",             "11",
               "https://www.qv-oerlikon.ch", "https://www.qv-oerlikon.ch/"),
    SiteConfig("qv_seebach",    "Quartierverein Seebach",                    "Seebach",              "11",
               "https://www.seebach.ch", "https://www.seebach.ch/"),
    SiteConfig("qv_schwamendingen","Quartierverein Schwamendingen",          "Schwamendingen",       "12",
               "https://www.qvs.ch", "https://www.qvs.ch/"),
]


# Volunteer-site path noise: events, calendars, photo galleries, login,
# member-only, generic legal pages. We keep substantive article-shaped
# pages (history, neighbourhood profile, projects).
_SKIP = (
    "/event", "/agenda", "/kalender", "/termin", "/programm",
    "/news", "/aktuell", "/blog/category", "/category/",
    "/galerie", "/gallery", "/fotos", "/bilder",
    "/login", "/anmeld", "/mitglied", "/spenden", "/shop",
    "/impressum", "/datenschutz", "/agb", "/kontakt",
    "/wp-content", "/wp-admin", "/wp-json", "/wp-login",
    "/feed", "/rss", "?p=", "?attachment_id=", "/print/",
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip",
)


def _link_filter_for(site: SiteConfig):
    def keep(url: str) -> bool:
        path = urlparse(url).path.lower()
        if any(s in path for s in _SKIP):
            return False
        if any(url.lower().endswith(ext) for ext in (".pdf", ".jpg", ".png", ".gif", ".zip")):
            return False
        return True
    return keep


def _subcategory_for_site(site: SiteConfig):
    def fn(url: str) -> Optional[str]:
        return f"{CATEGORY}/{site.slug}"
    return fn


def _tags_for_site(site: SiteConfig):
    quartier_tags = [p.strip().lower() for p in site.quartier.split("/")]

    def fn(title: str, text: str) -> list[str]:
        tags: list[str] = []
        tags.extend(quartier_tags)
        tags.append(f"kreis_{site.kreis}")
        t = (" " + title + " " + text[:600] + " ").lower()
        for kw in (
            "geschichte", "verein", "quartier", "stadtkreis", "kreis",
            "veranstaltung", "vorstand", "statuten", "projekt",
            "mitwirkung", "stadtentwicklung",
        ):
            if kw in t:
                tags.append(kw)
        return sorted(set(tags))

    return fn


def _run_site(site: SiteConfig, *, max_pages: int, dry_run: bool) -> dict:
    if dry_run:
        logger.info("[%s] dry-run prefix=%s seed=%s max=%d",
                    site.slug, site.url_prefix, site.seed, max_pages)
        return {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}

    cfg = CrawlConfig(
        seeds=[site.seed],
        url_prefix=site.url_prefix,
        max_pages=max_pages,
        max_depth=2,
        render=False,
        link_filter=_link_filter_for(site),
    )
    logger.info("[%s] crawl starting — max %d pages.", site.slug, max_pages)
    with Fetcher(rate_limit_seconds=1.5, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("[%s] crawl done. %d pages fetched.", site.slug, len(results))

    summary = make_and_write(
        category=CATEGORY,
        source_slug=site.slug,
        source_name=site.name,
        authority=AUTHORITY,
        language=LANGUAGE,
        results=results,
        subcategory_for=_subcategory_for_site(site),
        tags_for=_tags_for_site(site),
        ttl_days=TTL_DAYS,
    )
    logger.info("[%s] %s", site.slug, summary)
    return summary


def run(site_arg: str, limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if site_arg == "all":
        targets = SITES
    else:
        match = [s for s in SITES if s.slug == site_arg]
        if not match:
            logger.error("Unknown site '%s'. Choose from: %s, all",
                         site_arg, ", ".join(s.slug for s in SITES))
            return 2
        targets = match

    max_pages = limit if limit else 12
    grand = {"docs_written": 0, "total_chunks": 0, "procedures": 0, "articles": 0}
    for site in targets:
        try:
            s = _run_site(site, max_pages=max_pages, dry_run=dry_run)
        except Exception as e:
            logger.warning("[%s] crawl failed: %s — skipping", site.slug, e)
            continue
        for k, v in s.items():
            grand[k] += v

    logger.info("Grand total across %d sites: %s", len(targets), grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Quartiervereine into Phase 1 .jsonl")
    parser.add_argument("--site", default="all",
                        help="Slug of a single site (e.g. qv_affoltern), or 'all'.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Per-site page cap (0 = default 12). Conservative because volunteer sites are noisy.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(site_arg=args.site, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
