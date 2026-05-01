#!/usr/bin/env python3
"""parlament.ch ingester — Federal Assembly explainer pages.

Civic-bucket content covering how the Swiss Federal Assembly works:
roles of National Council and Council of States, the legislative
process, parliamentary instruments, sessions, committees. We stay on
the *explainer* tree and deliberately skip session protocols, vote
records, and curia-vista business databases — those are time-series
reference works better served by a live tool than a snapshot KB.

URL discovery: parlament.ch's sitemap.xml only covers news (5000
language-mixed press releases — useless for the KB). The real
explainer content lives under two trees discoverable from the
homepage navigation:

    /de/über-das-parlament    – institutional explainers
    /de/ratsbetrieb           – how parliament works (process)

We BFS from those two landing pages with depth=4, gated by an
allow-list on the URL-decoded path and an aggressive skip list for
archive/news/database trees.

Server-rendered with proper ``<h1>`` markup — no DOM surgery needed.

Usage:
    python -m scripts.ingest.parlament --dry-run
    python -m scripts.ingest.parlament --limit 30
    python -m scripts.ingest.parlament
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from typing import Optional
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from backend.kb.fetchers import Fetcher
from scripts.ingest._base import CrawlConfig, crawl, make_and_write

logger = logging.getLogger("zuribot.kb.ingest.parlament")

SOURCE_NAME = "Schweizer Parlament"
SOURCE_SLUG = "parlament"
AUTHORITY = "federal"
CATEGORY = "civic"
LANGUAGE = "de"
URL_PREFIX = "https://www.parlament.ch/de/"
TTL_DAYS = 365

SEED_URLS = (
    "https://www.parlament.ch/de/%C3%BCber-das-parlament-home",
    "https://www.parlament.ch/de/ratsbetrieb-home",
)

# Only these top-level branches carry evergreen explainer content.
# Path comparison happens on the URL-decoded path (Unicode ü, ä).
ALLOW_PATH_PREFIXES = (
    "/de/über-das-parlament",
    "/de/ratsbetrieb",
)

# Substrings that mark dynamic / time-series / database / archive
# content we explicitly do not want in the snapshot KB.
SKIP_PATH_SUBSTRINGS = (
    "/archiv",              # historical lists (presidiums, members, …)
    "/sessionen/",          # session-by-session protocols
    "/curia-vista",         # business database
    "/abstimmung",          # vote records
    "/geschaefte",          # individual business items
    "/vorstoesse",          # individual motion items
    "/suche",               # search pages
    "/services/",           # contact, parking, etc.
    "/medienmitteilung",    # news
    "/aktuell",
    "/agenda",
    "/wahlen-im-rueckblick",
    "/legislaturrueckblicke",
    "/fruehere-",
    "/ehemalige-",
    "/verstorbene-",
)

MAX_PATH_SEGMENTS = 6


def _normalise_html(html: bytes) -> bytes:
    """Reduce SharePoint chrome to <h1> + content div.

    parlament.ch is a classic SharePoint site: the page body is a giant
    <form> wrapper whose only meaningful content lives in a div whose id
    contains 'PublishingPageContent'. The site's ``<h1>`` element holds
    only an ARIA-hidden navigation label, so the visible page title comes
    from ``<title>``. We rebuild a clean body with one real <h1> and the
    content div, so extract_title_and_sections can do its thing.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
        title = re.sub(r"\s*[-|]\s*Schweiz\w*\s+Parlament.*$", "", title).strip()

    # Pick the largest div whose id contains "PublishingPageContent" — the
    # short one is just the "Seiteninhalt" form label; the real article is
    # the RichHtmlField wrapper.
    content = None
    best_len = 0
    for div in soup.find_all("div", id=True):  # skipcq: PYL-E1133  (bs4 ResultSet is iterable; pylint can't infer)
        if "PublishingPageContent" in div.get("id", ""):
            txt_len = len(div.get_text(" ", strip=True))
            if txt_len > best_len:
                best_len = txt_len
                content = div

    if not content or not title:
        return html

    new_soup = BeautifulSoup(
        "<html><body></body></html>", "html.parser"
    )
    h1 = new_soup.new_tag("h1")
    h1.string = title
    new_soup.body.append(h1)
    new_soup.body.append(content)
    return str(new_soup).encode("utf-8")


def _is_allowed(url: str) -> bool:
    if not url.startswith(URL_PREFIX):
        return False
    path = unquote(urlparse(url).path).lower()
    if not any(path.startswith(p) for p in ALLOW_PATH_PREFIXES):
        return False
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    if len([p for p in path.split("/") if p]) > MAX_PATH_SEGMENTS:
        return False
    return True


def _subcategory_for(url: str) -> Optional[str]:
    path = unquote(urlparse(url).path).lstrip("/").removeprefix("de/")
    parts = path.split("/")
    if not parts or not parts[0]:
        return None
    leaf = parts[0]
    leaf = (
        leaf.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            .replace("-", "_")
    )
    leaf = "".join(ch for ch in leaf if ch.isalnum() or ch == "_")
    if not leaf:
        return None
    return f"{CATEGORY}/{leaf}"


def _tags_for(title: str, text: str) -> list[str]:
    tags: list[str] = []
    t = (" " + title + " " + text[:600] + " ").lower()
    for kw in (
        "nationalrat", "staenderat", "ständerat", "bundesversammlung",
        "kommission", "fraktion", "session", "ratsbetrieb", "vorstoss",
        "motion", "interpellation", "initiative", "referendum",
        "vernehmlassung", "gesetzgebung", "bundesrat",
    ):
        if kw in t:
            tags.append(kw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))
    # Dedupe while preserving order.
    seen: set[str] = set()
    return [x for x in tags if not (x in seen or seen.add(x))]


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    max_pages = limit if limit else 250

    if dry_run:
        logger.info("BFS seeds:")
        for u in SEED_URLS:
            logger.info("    %s", u)
        logger.info("max_pages=%d, max_depth=4", max_pages)
        return 0

    cfg = CrawlConfig(
        seeds=list(SEED_URLS),
        url_prefix=URL_PREFIX,
        max_pages=max_pages,
        max_depth=4,
        render=False,
        link_filter=_is_allowed,
    )

    logger.info("Crawl starting — %d seeds, max=%d.", len(SEED_URLS), max_pages)
    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        results = crawl(fetcher, cfg)
    logger.info("Crawl done. %d pages fetched.", len(results))

    # parlament.ch leaves <h1> empty and serves the title only via <title>.
    # Inject it so extract_title_and_sections finds something.
    for r in results:
        try:
            r.content = _normalise_html(r.content)
        except Exception as e:
            logger.warning("normalise failed url=%s err=%s", r.url, e)

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
    parser = argparse.ArgumentParser(description="Ingest parlament.ch into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap URLs (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
