#!/usr/bin/env python3
"""Food & drink reference ingester.

Curated reference pages about Zürich's gastronomy landscape:

  • Gault Millau Schweiz — editorial framework (Hot Ten, Zürich
    Isst, redaktionelles Profil) — gives Bünzli the concept
    vocabulary to talk about restaurants without claiming current
    rankings.
  • Harrys Ding (harrysding.ch) — long-running Zürich
    restaurant/food blog. We harvest the ``restaurants-zuerich``
    category (paginated) and emit each post as one ``article``
    chunk. Provides texture and review-style copy that pairs well
    with Bünzli's chatty register.

Out of scope: Stadt Zürich Wochenmärkte — the city has no clean
crawlable market page (the /maerkte and /wirtschaft trees all
404). Market info today comes via the zuerich.com ingester. A
dedicated municipal-markets ingester is deferred.

JS-rendered SPAs use the plain-then-Playwright fallback pattern
shared with ``emergency_refs.py`` and ``leisure_refs.py``.

Usage
-----

    python -m scripts.ingest.food_drink_refs --dry-run
    python -m scripts.ingest.food_drink_refs --site gastrozuerich
    python -m scripts.ingest.food_drink_refs
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

logger = logging.getLogger("zuribot.kb.ingest.food_drink_refs")

CATEGORY = "food_drink"
LANGUAGE = "de"


@dataclass
class SiteEntry:
    url: str
    entity_name: str
    entity_type: str
    title_override: Optional[str] = None
    subcategory: Optional[str] = None
    tags: list[str] = None  # type: ignore[assignment]
    # Some discovery functions fetch the page to filter (e.g. by PLZ).
    # When set, the main loop reuses these bytes instead of re-fetching.
    prefetched_html: Optional[bytes] = None


@dataclass
class SiteConfig:
    slug: str
    source_name: str
    authority: str
    ttl_days: Optional[int]
    entries: list[SiteEntry]
    # Optional: dynamic URL discovery. When set, the driver calls this
    # to build entries on the fly (paginated blog category, etc.).
    discover: Optional[object] = None
    doc_type: str = "reference"


_GAULTMILLAU_META = [
    SiteEntry(
        url="https://www.gaultmillau.ch/",
        entity_name="Gault Millau Schweiz",
        entity_type="Restaurantführer",
        title_override="Gault Millau Schweiz — Übersicht",
        subcategory="food_drink/guides",
        tags=["gaultmillau", "restaurantfuehrer", "gastronomie"],
    ),
    SiteEntry(
        url="https://www.gaultmillau.ch/restaurants",
        entity_name="Gault Millau — Restaurants",
        entity_type="Restaurantführer",
        title_override="Gault Millau — Restaurants (Bewertungssystem)",
        subcategory="food_drink/guides",
        tags=["gaultmillau", "restaurants", "punkte", "bewertung"],
    ),
    SiteEntry(
        url="https://www.gaultmillau.ch/zueri-isst",
        entity_name="Gault Millau — Züri isst",
        entity_type="Restaurantführer",
        title_override="Gault Millau — Züri isst (Zürich-Sektion)",
        subcategory="food_drink/guides",
        tags=["gaultmillau", "zueri", "zuerich", "restaurants"],
    ),
    SiteEntry(
        url="https://www.gaultmillau.ch/hot-ten",
        entity_name="Gault Millau — Hot Ten",
        entity_type="Restaurantführer",
        title_override="Gault Millau — Hot Ten Listen",
        subcategory="food_drink/guides",
        tags=["gaultmillau", "hot-ten", "listen"],
    ),
    SiteEntry(
        url="https://www.gaultmillau.ch/unsere-redaktion",
        entity_name="Gault Millau — Redaktion",
        entity_type="Restaurantführer",
        title_override="Gault Millau — Unsere Redaktion",
        subcategory="food_drink/guides",
        tags=["gaultmillau", "redaktion", "ueberuns"],
    ),
]


_PLZ_ZH_RE = __import__("re").compile(r"\b8\d{3}\b")


def _discover_gaultmillau_zurich(fetcher: Fetcher, max_pages: int) -> list[SiteEntry]:
    """Walk gaultmillau.ch sitemap, fetch each restaurant detail page,
    keep only those with a Zürich-canton PLZ (8000-8999) in the body.

    The sitemap index lists ~100 monthly sub-sitemaps; together they
    contain ~860 unique restaurant detail URLs across all of Switzerland.
    Detail pages return clean review prose via plain HTTP — no Playwright
    needed. Filtering by PLZ inline avoids over-ingesting French-CH or
    Tessin restaurants while staying simple.

    ``max_pages`` caps the number of detail-page candidates probed (0 = no cap).
    """
    import re
    from urllib.parse import urljoin

    INDEX = "https://www.gaultmillau.ch/sitemap.xml"
    LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
    DETAIL_RE = re.compile(r"/restaurants/[^/]+-\d+/?$")

    res = fetcher.fetch(INDEX)
    if res is None or res.status_code != 200:
        logger.warning("[gaultmillau] sitemap index fetch failed")
        return []
    sub_sitemaps = LOC_RE.findall(res.content.decode("utf-8", "ignore"))
    logger.info("[gaultmillau] sitemap index: %d sub-sitemaps", len(sub_sitemaps))

    detail_urls: list[str] = []
    seen: set[str] = set()
    for sm in sub_sitemaps:
        rr = fetcher.fetch(sm)
        if rr is None or rr.status_code != 200:
            continue
        for u in LOC_RE.findall(rr.content.decode("utf-8", "ignore")):
            u = u.rstrip("/")
            if DETAIL_RE.search(u + "/") and u not in seen:
                seen.add(u)
                detail_urls.append(u)
    logger.info("[gaultmillau] %d candidate restaurant URLs across sitemaps",
                len(detail_urls))

    if max_pages and max_pages > 0:
        detail_urls = detail_urls[:max_pages]

    out: list[SiteEntry] = []
    for i, url in enumerate(detail_urls, 1):
        rr = fetcher.fetch(url)
        if rr is None or rr.status_code != 200:
            continue
        soup = BeautifulSoup(rr.content, "html.parser")
        for sel in ("script", "style", "nav", "header", "footer", "aside"):
            for tag in soup.select(sel):
                tag.decompose()
        main = soup.select_one("main") or soup.body or soup
        text_head = main.get_text("\n", strip=True)[:1000] if main else ""

        # PLZ filter — Zürich canton is 8000-8999. Extra-canton PLZs
        # starting with 8 (e.g. 8580 Amriswil TG) exist but are rare;
        # the false-positive rate is low enough to not bother with a
        # canton list.
        if not _PLZ_ZH_RE.search(text_head):
            if i % 50 == 0:
                logger.info("[gaultmillau] %d/%d probed, %d ZH so far",
                            i, len(detail_urls), len(out))
            continue

        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else url.rsplit("/", 1)[-1]
        slug = url.rsplit("/", 1)[-1]
        out.append(SiteEntry(
            url=url,
            entity_name=name,
            entity_type="Restaurant",
            title_override=f"Gault Millau — {name}",
            subcategory="food_drink/restaurants",
            tags=["gaultmillau", "restaurant", "zuerich", "review"],
            prefetched_html=rr.content,
        ))
        if i % 50 == 0:
            logger.info("[gaultmillau] %d/%d probed, %d ZH so far",
                        i, len(detail_urls), len(out))
    logger.info("[gaultmillau] kept %d Zürich-canton restaurants out of %d",
                len(out), len(detail_urls))
    return out


GAULTMILLAU = SiteConfig(
    slug="gaultmillau",
    source_name="Gault Millau Schweiz",
    authority="community",
    ttl_days=180,
    entries=_GAULTMILLAU_META,
    discover=_discover_gaultmillau_zurich,
)


def _discover_harrysding(fetcher: Fetcher, max_pages: int) -> list[SiteEntry]:
    """Walk harrysding.ch /category/restaurants-zuerich/page/N until empty.

    The site is JS-rendered, so we use Playwright. Each post becomes
    one SiteEntry; the title and tags are filled later from the page.
    """
    base = "https://harrysding.ch/category/restaurants-zuerich/"
    seen: set[str] = set()
    out: list[SiteEntry] = []
    for p in range(1, max_pages + 1):
        url = base if p == 1 else f"{base}page/{p}/"
        rendered = fetcher.fetch_rendered(url, wait_until="domcontentloaded",
                                          wait_ms=2000)
        if rendered is None or rendered.status_code != 200:
            break
        soup = BeautifulSoup(rendered.content, "html.parser")
        new_here = 0
        for h in soup.find_all(["h2", "h3"]):
            a = h.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if "harrysding.ch/20" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            slug = href.rstrip("/").rsplit("/", 1)[-1]
            out.append(SiteEntry(
                url=href,
                entity_name=f"Harrys Ding — {slug}",
                entity_type="Restaurant-Review",
                title_override=None,
                subcategory="food_drink/reviews",
                tags=["harrysding", "review", "zuerich"],
            ))
            new_here += 1
        logger.info("[harrysding] page=%d new=%d total=%d", p, new_here, len(out))
        if new_here == 0:
            break
    return out


HARRYSDING = SiteConfig(
    slug="harrysding",
    source_name="Harrys Ding",
    authority="community",
    ttl_days=180,
    entries=[],  # filled at runtime via discover
    discover=_discover_harrysding,
    doc_type="article",
)


SITES: dict[str, SiteConfig] = {
    "gaultmillau": GAULTMILLAU,
    "harrysding": HARRYSDING,
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

    with Fetcher(rate_limit_seconds=1.0, timeout=25) as fetcher:
        entries = list(site.entries)
        if site.discover is not None:
            max_pages = limit if limit else 0
            discovered = site.discover(fetcher, max_pages)  # type: ignore[misc]
            entries = entries + discovered
        elif limit:
            entries = entries[:limit]

        if dry_run:
            for e in entries:
                logger.info("  %s -> %s [%s]", e.url, e.entity_name,
                            e.entity_type)
            return {"docs_written": 0, "total_chunks": 0, "skipped": 0,
                    "site": site.slug, "planned": len(entries)}

        for entry in entries:
            html = entry.prefetched_html if entry.prefetched_html is not None \
                else _fetch_with_fallback(fetcher, entry.url)
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
                doc_type=site.doc_type,  # type: ignore[arg-type]
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
        description="Ingest food & drink reference sites "
                    "(Gault Millau, Harrys Ding).")
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
