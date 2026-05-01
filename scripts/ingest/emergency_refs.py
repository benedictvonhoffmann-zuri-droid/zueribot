#!/usr/bin/env python3
"""Emergency reference ingester — Tox Info Suisse.

Tox Info Suisse (toxinfo.ch) is the federal poison-control hotline.
Stable reference content: hotline number 145, when to call, first
aid by exposure type, antidote/antivenin info, organisation portrait.
Each curated page becomes one ``reference`` chunk per spec §5.3.

A previous version also scraped apotheken-notfall.ch but that domain
went dead (NXDOMAIN) and there is no clean federal pharmacy-emergency
portal — pharmavista, 144.ch and similar sites are SPAs without
crawlable content. Pharmacy emergency lookups will likely become a
live tool rather than a KB lookup.

URL discovery: tiny curated list — toxinfo's site is small and the
high-value pages are hand-pickable.

Render mode: plain HTTP first; falls back to Playwright if the plain
fetch returns < 500 chars of body text (i.e. JS-rendered shell).

Usage
-----

    python -m scripts.ingest.emergency_refs --dry-run
    python -m scripts.ingest.emergency_refs --limit 3
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

logger = logging.getLogger("zuribot.kb.ingest.emergency_refs")

CATEGORY = "emergency"
LANGUAGE = "de"

# Per-site config ──────────────────────────────────────────────────────────


@dataclass
class SiteEntry:
    url: str
    entity_name: str
    entity_type: str  # e.g. "Notfall-Hotline", "Notfallapotheke"
    title_override: Optional[str] = None  # use when DOM lacks a usable h1
    subcategory: Optional[str] = None
    tags: list[str] = None  # type: ignore[assignment]


@dataclass
class SiteConfig:
    slug: str          # data/chunks/emergency/<slug>/
    source_name: str
    authority: str     # 'federal' | 'community'
    ttl_days: Optional[int]
    entries: list[SiteEntry]


TOX = SiteConfig(
    slug="toxinfo",
    source_name="Tox Info Suisse",
    authority="federal",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.toxinfo.ch/notruf-145",
            entity_name="Tox Info Suisse — Notruf 145",
            entity_type="Notfall-Hotline",
            title_override="Tox Info Suisse — Notruf 145",
            subcategory="emergency/giftnotruf",
            tags=["giftnotruf", "145", "vergiftung", "notfall"],
        ),
        SiteEntry(
            url="https://www.toxinfo.ch/erste_hilfe",
            entity_name="Tox Info Suisse — Erste Hilfe",
            entity_type="Erste-Hilfe-Anleitung",
            title_override="Tox Info Suisse — Erste Hilfe bei Vergiftungen",
            subcategory="emergency/giftnotruf",
            tags=["erstehilfe", "vergiftung", "145"],
        ),
        SiteEntry(
            url="https://www.toxinfo.ch/portrait",
            entity_name="Tox Info Suisse — Portrait",
            entity_type="Institution",
            title_override="Tox Info Suisse — Über die Stiftung",
            subcategory="emergency/giftnotruf",
            tags=["tox", "stiftung", "portrait"],
        ),
        SiteEntry(
            url="https://www.toxinfo.ch/antidot",
            entity_name="Tox Info Suisse — Antidote",
            entity_type="Fachreferenz",
            title_override="Tox Info Suisse — Antidote",
            subcategory="emergency/giftnotruf",
            tags=["antidot", "vergiftung"],
        ),
        SiteEntry(
            url="https://www.toxinfo.ch/antivenin",
            entity_name="Tox Info Suisse — Antivenin",
            entity_type="Fachreferenz",
            title_override="Tox Info Suisse — Antivenin (Schlangenbissserum)",
            subcategory="emergency/giftnotruf",
            tags=["antivenin", "schlange", "vergiftung"],
        ),
        SiteEntry(
            url="https://www.toxinfo.ch/startseite",
            entity_name="Tox Info Suisse — Startseite",
            entity_type="Notfall-Hotline",
            title_override="Tox Info Suisse — Übersicht",
            subcategory="emergency/giftnotruf",
            tags=["giftnotruf", "tox"],
        ),
    ],
)

DARGEBOTENE_HAND = SiteConfig(
    slug="dargebotene_hand",
    source_name="Die Dargebotene Hand 143",
    authority="community",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.143.ch/",
            entity_name="Tel 143 — Die Dargebotene Hand",
            entity_type="Notfall-Hotline",
            title_override="Tel 143 — Die Dargebotene Hand",
            subcategory="emergency/seelsorge",
            tags=["143", "krise", "seelsorge", "notfall"],
        ),
        SiteEntry(
            url="https://www.143.ch/ueber-uns/",
            entity_name="Tel 143 — Über uns",
            entity_type="Institution",
            title_override="Tel 143 — Über uns",
            subcategory="emergency/seelsorge",
            tags=["143", "stiftung", "portrait"],
        ),
    ],
)

PRO_JUVENTUTE = SiteConfig(
    slug="pro_juventute_147",
    source_name="Pro Juventute 147",
    authority="community",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.147.ch/",
            entity_name="Pro Juventute 147 — Beratung für Jugendliche",
            entity_type="Notfall-Hotline",
            title_override="Pro Juventute 147 — Beratung für Kinder und Jugendliche",
            subcategory="emergency/jugendberatung",
            tags=["147", "jugend", "kinder", "krise", "beratung"],
        ),
    ],
)

REDEN_KANN_RETTEN = SiteConfig(
    slug="reden_kann_retten",
    source_name="Reden kann retten — Suizidprävention",
    authority="community",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.reden-kann-retten.ch/",
            entity_name="Reden kann retten",
            entity_type="Notfall-Hotline",
            title_override="Reden kann retten — Suizidprävention Schweiz",
            subcategory="emergency/suizidpraevention",
            tags=["suizid", "praevention", "krise", "143"],
        ),
    ],
)

REGA = SiteConfig(
    slug="rega",
    source_name="Schweizerische Rettungsflugwacht Rega",
    authority="community",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.rega.ch/",
            entity_name="Rega — Notruf 1414",
            entity_type="Notfall-Hotline",
            title_override="Rega — Schweizerische Rettungsflugwacht",
            subcategory="emergency/luftrettung",
            tags=["rega", "1414", "luftrettung", "notfall"],
        ),
    ],
)

USZ_NOTFALL = SiteConfig(
    slug="usz_notfall",
    source_name="UniversitätsSpital Zürich — Notfallzentrum",
    authority="cantonal",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.usz.ch/notfall/",
            entity_name="USZ — Notfallzentrum",
            entity_type="Notfallstation",
            title_override="USZ — Notfallzentrum (Erwachsene)",
            subcategory="emergency/spital_notfall",
            tags=["usz", "notfall", "spital", "erwachsene"],
        ),
    ],
)

KISPI_NOTFALL = SiteConfig(
    slug="kispi_notfall",
    source_name="Kinderspital Zürich — Notfall",
    authority="cantonal",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.kispi.uzh.ch/notfall",
            entity_name="Kispi — Notfallstation",
            entity_type="Notfallstation",
            title_override="Kinderspital Zürich — Notfall",
            subcategory="emergency/spital_notfall",
            tags=["kispi", "kinder", "notfall", "spital"],
        ),
    ],
)

KAPO_ZH = SiteConfig(
    slug="kapo_zh",
    source_name="Kantonspolizei Zürich",
    authority="cantonal",
    ttl_days=None,
    entries=[
        SiteEntry(
            url="https://www.zh.ch/de/sicherheitsdirektion/kantonspolizei-zuerich.html",
            entity_name="Kantonspolizei Zürich",
            entity_type="Polizei",
            title_override="Kantonspolizei Zürich",
            subcategory="emergency/polizei",
            tags=["polizei", "117", "kapo", "kanton"],
        ),
    ],
)

SITES: dict[str, SiteConfig] = {
    "tox": TOX,
    "dargebotene_hand": DARGEBOTENE_HAND,
    "pro_juventute_147": PRO_JUVENTUTE,
    "reden_kann_retten": REDEN_KANN_RETTEN,
    "rega": REGA,
    "usz_notfall": USZ_NOTFALL,
    "kispi_notfall": KISPI_NOTFALL,
    "kapo_zh": KAPO_ZH,
}


# Extraction ───────────────────────────────────────────────────────────────


def _extract_text(html: bytes) -> tuple[str, str]:
    """Return (title, body_text). Body is the visible textual payload.

    Reference docs are short — we don't need section structure, just
    a clean blob that the chunker emits as one chunk. We do however
    drop boilerplate like nav/footer/scripts.
    """
    title, _sections, full = extract_title_and_sections(html)
    if full and len(full) >= 200:
        return title, full

    # Fallback: take main/body text directly. extract_title_and_sections
    # already strips nav/footer/scripts.
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
    """Plain HTTP first; Playwright if body looks like a JS shell."""
    res = fetcher.fetch(url)
    if res is not None and res.status_code == 200:
        _, body = _extract_text(res.content)
        if len(body) >= 500:
            return res.content
        logger.info("plain HTTP body=%d chars; trying rendered fetch for %s",
                    len(body), url)

    rendered = fetcher.fetch_rendered(url, wait_until="domcontentloaded",
                                      wait_ms=1500)
    if rendered is not None and rendered.status_code == 200:
        return rendered.content
    return None


# Driver ───────────────────────────────────────────────────────────────────


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

    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
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
            logger.error("unknown --site %s (use tox|all)", site)
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
        description="Ingest emergency reference sites (Tox Info Suisse, "
                    "Apotheken-Notfalldienst) into Phase 1 .jsonl.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap entries per site (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned URLs; don't fetch")
    parser.add_argument("--site", choices=tuple(SITES.keys()) + ("all",),
                        default="all",
                        help="Which site to ingest (default: all)")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run, site=args.site)


if __name__ == "__main__":
    sys.exit(main())
