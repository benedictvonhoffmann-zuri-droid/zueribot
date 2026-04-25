#!/usr/bin/env python3
"""Leisure reference ingester — Zürich museums and city pools.

Marquee Zürich leisure institutions whose stable identity pages —
opening hours, admission, mission, current programme — give Bünzli
enough texture to talk about "what to do in Zürich" without scraping
event calendars (those live in a future events ingester).

Sites covered:
  • Kunsthaus Zürich (kunsthaus.ch)
  • Museum Rietberg (rietberg.ch)
  • Schweizerisches Landesmuseum / Landesmuseum Zürich
  • Stadt Zürich Sport- und Badeanlagen (city pools / Badis)

Most of these are JS-rendered SPAs; we use the same plain-then-rendered
fallback pattern as ``emergency_refs.py``.

Usage
-----

    python -m scripts.ingest.leisure_refs --dry-run
    python -m scripts.ingest.leisure_refs --site rietberg
    python -m scripts.ingest.leisure_refs
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from backend.kb.chunker import Document, chunk_document
from backend.kb.fetchers import Fetcher
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT, extract_title_and_sections

logger = logging.getLogger("zuribot.kb.ingest.leisure_refs")

CATEGORY = "leisure"
LANGUAGE = "de"


@dataclass
class SiteEntry:
    url: str
    entity_name: str
    entity_type: str
    title_override: Optional[str] = None
    subcategory: Optional[str] = None
    tags: list[str] = None  # type: ignore[assignment]


@dataclass
class SiteConfig:
    slug: str
    source_name: str
    authority: str
    ttl_days: Optional[int]
    entries: list[SiteEntry]


KUNSTHAUS = SiteConfig(
    slug="kunsthaus",
    source_name="Kunsthaus Zürich",
    authority="community",
    ttl_days=180,
    entries=[
        SiteEntry(
            url="https://www.kunsthaus.ch/de/",
            entity_name="Kunsthaus Zürich",
            entity_type="Museum",
            title_override="Kunsthaus Zürich — Übersicht",
            subcategory="leisure/museums",
            tags=["museum", "kunst", "kunsthaus", "zuerich"],
        ),
        SiteEntry(
            url="https://www.kunsthaus.ch/de/sammlung/",
            entity_name="Kunsthaus Zürich — Sammlung",
            entity_type="Museum",
            title_override="Kunsthaus Zürich — Sammlung",
            subcategory="leisure/museums",
            tags=["museum", "sammlung", "kunsthaus"],
        ),
    ],
)

RIETBERG = SiteConfig(
    slug="rietberg",
    source_name="Museum Rietberg",
    authority="community",
    ttl_days=180,
    entries=[
        SiteEntry(
            url="https://rietberg.ch/",
            entity_name="Museum Rietberg",
            entity_type="Museum",
            title_override="Museum Rietberg — Übersicht",
            subcategory="leisure/museums",
            tags=["museum", "rietberg", "aussereuropaeisch"],
        ),
        SiteEntry(
            url="https://rietberg.ch/museum",
            entity_name="Museum Rietberg — Über das Museum",
            entity_type="Museum",
            title_override="Museum Rietberg — Über das Museum",
            subcategory="leisure/museums",
            tags=["museum", "rietberg", "geschichte"],
        ),
        SiteEntry(
            url="https://rietberg.ch/ausstellungen",
            entity_name="Museum Rietberg — Ausstellungen",
            entity_type="Museum",
            title_override="Museum Rietberg — Ausstellungen",
            subcategory="leisure/museums",
            tags=["museum", "ausstellung", "rietberg"],
        ),
        SiteEntry(
            url="https://rietberg.ch/sammlung",
            entity_name="Museum Rietberg — Sammlung",
            entity_type="Museum",
            title_override="Museum Rietberg — Sammlung",
            subcategory="leisure/museums",
            tags=["museum", "sammlung", "rietberg"],
        ),
        SiteEntry(
            url="https://rietberg.ch/besuch",
            entity_name="Museum Rietberg — Besuch",
            entity_type="Museum",
            title_override="Museum Rietberg — Besuch (Öffnungszeiten, Eintritt)",
            subcategory="leisure/museums",
            tags=["museum", "besuch", "oeffnungszeiten", "rietberg"],
        ),
    ],
)

LANDESMUSEUM = SiteConfig(
    slug="landesmuseum",
    source_name="Schweizerisches Landesmuseum",
    authority="federal",
    ttl_days=180,
    entries=[
        SiteEntry(
            url="https://www.landesmuseum.ch/de",
            entity_name="Landesmuseum Zürich",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Übersicht",
            subcategory="leisure/museums",
            tags=["museum", "landesmuseum", "geschichte", "schweiz"],
        ),
        SiteEntry(
            url="https://www.landesmuseum.ch/de/ihr-besuch",
            entity_name="Landesmuseum Zürich — Ihr Besuch",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Ihr Besuch",
            subcategory="leisure/museums",
            tags=["museum", "besuch", "landesmuseum"],
        ),
        SiteEntry(
            url="https://www.landesmuseum.ch/de/ihr-besuch/oeffnungszeiten",
            entity_name="Landesmuseum Zürich — Öffnungszeiten",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Öffnungszeiten und Eintritt",
            subcategory="leisure/museums",
            tags=["museum", "oeffnungszeiten", "eintritt", "landesmuseum"],
        ),
        SiteEntry(
            url="https://www.landesmuseum.ch/de/ihr-besuch/besucherinfos",
            entity_name="Landesmuseum Zürich — Besucherinfos",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Besucherinformationen",
            subcategory="leisure/museums",
            tags=["museum", "besuch", "landesmuseum"],
        ),
        SiteEntry(
            url="https://www.landesmuseum.ch/de/ihr-besuch/ausstellungen",
            entity_name="Landesmuseum Zürich — Ausstellungen",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Ausstellungen",
            subcategory="leisure/museums",
            tags=["museum", "ausstellung", "landesmuseum"],
        ),
        SiteEntry(
            url="https://www.landesmuseum.ch/de/ueber-uns/geschichte",
            entity_name="Landesmuseum Zürich — Geschichte",
            entity_type="Museum",
            title_override="Landesmuseum Zürich — Geschichte des Hauses",
            subcategory="leisure/museums",
            tags=["museum", "geschichte", "landesmuseum"],
        ),
    ],
)

BADIS = SiteConfig(
    slug="badis",
    source_name="Stadt Zürich — Sport- und Badeanlagen",
    authority="city",
    ttl_days=180,
    entries=[
        SiteEntry(
            url="https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/sport-und-badeanlagen.html",
            entity_name="Stadt Zürich — Sport- und Badeanlagen",
            entity_type="Sport-/Badeanlage",
            title_override="Stadt Zürich — Sport- und Badeanlagen (Übersicht)",
            subcategory="leisure/badis",
            tags=["badi", "schwimmbad", "sportamt", "zuerich"],
        ),
        SiteEntry(
            url="https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/sport-und-badeanlagen/sommerbaeder.html",
            entity_name="Stadt Zürich — Sommerbäder",
            entity_type="Sport-/Badeanlage",
            title_override="Stadt Zürich — Sommerbäder (Freibäder, Seebäder, Flussbäder)",
            subcategory="leisure/badis",
            tags=["badi", "sommerbad", "freibad", "seebad", "flussbad"],
        ),
        SiteEntry(
            url="https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/sport-und-badeanlagen/hallenbaeder.html",
            entity_name="Stadt Zürich — Hallenbäder",
            entity_type="Sport-/Badeanlage",
            title_override="Stadt Zürich — Hallenbäder",
            subcategory="leisure/badis",
            tags=["badi", "hallenbad", "schwimmbad"],
        ),
        SiteEntry(
            url="https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/sport-und-badeanlagen/preise-abos.html",
            entity_name="Stadt Zürich — Bäder-Preise und Abos",
            entity_type="Sport-/Badeanlage",
            title_override="Stadt Zürich — Bäder-Preise und Abos",
            subcategory="leisure/badis",
            tags=["badi", "preise", "abo", "eintritt"],
        ),
        SiteEntry(
            url="https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/sport-und-badeanlagen/verhaltensregeln-badeanlagen.html",
            entity_name="Stadt Zürich — Verhaltensregeln Badeanlagen",
            entity_type="Sport-/Badeanlage",
            title_override="Stadt Zürich — Verhaltensregeln in Badeanlagen",
            subcategory="leisure/badis",
            tags=["badi", "regeln", "hausordnung"],
        ),
    ],
)

SITES: dict[str, SiteConfig] = {
    "kunsthaus": KUNSTHAUS,
    "rietberg": RIETBERG,
    "landesmuseum": LANDESMUSEUM,
    "badis": BADIS,
}


def _extract_text(html: bytes) -> tuple[str, str]:
    title, _sections, full = extract_title_and_sections(html)
    if full and len(full) >= 200:
        return title, full

    soup = BeautifulSoup(html, "html.parser")
    for sel in ("script", "style", "nav", "header", "footer", "aside",
                "noscript", "form", "iframe"):
        for tag in soup.select(sel):
            tag.decompose()
    main = soup.select_one("main") or soup.body or soup
    text = main.get_text("\n", strip=True) if main else ""
    if not title:
        h = soup.find("h1") or soup.find("title")
        if h:
            title = h.get_text(" ", strip=True)
    return title or "", text


def _fetch_with_fallback(fetcher: Fetcher, url: str) -> Optional[bytes]:
    res = fetcher.fetch(url)
    if res is not None and res.status_code == 200:
        _, body = _extract_text(res.content)
        if len(body) >= 500:
            return res.content
        logger.info("plain HTTP body=%d chars; trying rendered fetch for %s",
                    len(body), url)

    rendered = fetcher.fetch_rendered(url, wait_until="domcontentloaded",
                                      wait_ms=2500)
    if rendered is not None and rendered.status_code == 200:
        return rendered.content
    return None


def _ingest_site(site: SiteConfig, limit: int, dry_run: bool) -> dict:
    today = date.today()
    written = 0
    chunks_total = 0
    skipped = 0

    entries = site.entries
    if limit:
        entries = entries[:limit]

    if dry_run:
        for e in entries:
            logger.info("  %s -> %s [%s]", e.url, e.entity_name, e.entity_type)
        return {"docs_written": 0, "total_chunks": 0, "skipped": 0,
                "site": site.slug, "planned": len(entries)}

    with Fetcher(rate_limit_seconds=1.0, timeout=25) as fetcher:
        for entry in entries:
            html = _fetch_with_fallback(fetcher, entry.url)
            if html is None:
                logger.warning("fetch failed url=%s", entry.url)
                skipped += 1
                continue

            title, body = _extract_text(html)
            title = entry.title_override or title or entry.entity_name
            if not body or len(body) < 200:
                logger.info("skip (empty page) url=%s body=%d",
                            entry.url, len(body))
                skipped += 1
                continue

            doc = Document(
                source_url=entry.url,
                source_name=site.source_name,
                title=title,
                language=LANGUAGE,
                category=CATEGORY,  # type: ignore[arg-type]
                authority=site.authority,  # type: ignore[arg-type]
                doc_type="reference",  # type: ignore[arg-type]
                text=body,
                subcategory=entry.subcategory,
                tags=entry.tags or [],
                created_at=today,
                updated_at=today,
                ttl_days=site.ttl_days,
                entity_name=entry.entity_name,
                entity_type=entry.entity_type,
            )
            try:
                chunks = chunk_document(doc)
            except Exception as e:  # pragma: no cover
                logger.warning("chunk failed url=%s err=%s", entry.url, e)
                skipped += 1
                continue

            write_chunks(chunks, CHUNKS_ROOT, CATEGORY, site.slug)
            written += 1
            chunks_total += len(chunks)

    return {
        "site": site.slug,
        "docs_written": written,
        "total_chunks": chunks_total,
        "skipped": skipped,
    }


def run(limit: int, dry_run: bool, site: str) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if site == "all":
        targets = list(SITES.values())
    else:
        if site not in SITES:
            logger.error("unknown --site %s (use %s|all)",
                         site, "|".join(SITES))
            return 2
        targets = [SITES[site]]

    grand = {"docs_written": 0, "total_chunks": 0, "skipped": 0}
    for cfg in targets:
        logger.info("=== %s (%s, authority=%s, ttl=%s) ===",
                    cfg.source_name, cfg.slug, cfg.authority, cfg.ttl_days)
        summary = _ingest_site(cfg, limit, dry_run)
        logger.info("site summary: %s", summary)
        for k in ("docs_written", "total_chunks", "skipped"):
            grand[k] += summary.get(k, 0)
    logger.info("Total: %s", grand)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest leisure reference sites (Zürich museums, Badis).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap entries per site (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned URLs; don't fetch")
    parser.add_argument("--site",
                        choices=tuple(SITES) + ("all",),
                        default="all",
                        help="Which site to ingest (default: all)")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run, site=args.site)


if __name__ == "__main__":
    sys.exit(main())
