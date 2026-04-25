#!/usr/bin/env python3
"""swissvotes.ch ingester — federal vote database.

Each federal popular vote (since 1848) becomes one ``reference``
chunk: title, date, type, recommendations, and the official result.
Reference doc_type means one entity = one chunk, never split — that
matches a vote's identity perfectly.

URL discovery: swissvotes.ch publishes a votes index page. We harvest
all ``/vote/<id>`` links from it, then fetch each vote-detail page
in DE only. (The site exposes FR/IT/EN variants under language-prefixed
paths — we ignore them.)

Out of scope: statistical dashboards, dataset downloads, admin pages.
The full historical crawl (~700 votes) is deferred to the AI pod;
default ``--limit`` keeps smoke runs cheap.

Usage:
    python -m scripts.ingest.swissvotes --dry-run
    python -m scripts.ingest.swissvotes --limit 10
    python -m scripts.ingest.swissvotes
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from backend.kb.chunker import Document, chunk_document
from backend.kb.fetchers import Fetcher
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks
from scripts.ingest._base import CHUNKS_ROOT

logger = logging.getLogger("zuribot.kb.ingest.swissvotes")

SOURCE_NAME = "Swissvotes"
SOURCE_SLUG = "swissvotes"
AUTHORITY = "federal"
CATEGORY = "civic"
LANGUAGE = "de"
TTL_DAYS = 180

BASE = "https://swissvotes.ch"
INDEX_URL = f"{BASE}/votes"
# Detail pages live at /vote/<numeric id>; the id can be a float
# string like "684.00" (and "682.20" for sub-votes). The index
# emits absolute URLs so we match the full href.
VOTE_HREF_RE = re.compile(r'href="(https://swissvotes\.ch/vote/[0-9.]+)"')

# Path substrings on the detail page we drop before extraction.
SKIP_PATH_SUBSTRINGS = (
    "/page/",        # static info pages
    "/dataset",      # statistical dashboards & downloads
    "/login",
    "/admin",
)


def _fetch_index_urls(timeout: int = 30, max_pages: int = 60) -> list[str]:
    """Walk /votes?page=N until no new vote URLs appear."""
    logger.info("Fetching %s …", INDEX_URL)
    seen: set[str] = set()
    out: list[str] = []
    for p in range(0, max_pages):
        u = f"{INDEX_URL}?page={p}"
        try:
            resp = requests.get(u, timeout=timeout)
        except requests.RequestException as e:
            logger.warning("index fetch failed url=%s err=%s", u, e)
            break
        if not resp.ok:
            break
        new_here = 0
        for full in VOTE_HREF_RE.findall(resp.text):
            if full not in seen:
                seen.add(full)
                out.append(full)
                new_here += 1
        if p % 10 == 0:
            logger.info("  page=%d new=%d total=%d", p, new_here, len(out))
        if new_here == 0 and p > 1:
            break
    logger.info("index: %d distinct vote URLs", len(out))
    return out


def _extract_vote(html: bytes, url: str) -> Optional[tuple[str, str]]:
    """Return (title, summary_text) for a vote-detail page, or None to skip."""
    soup = BeautifulSoup(html, "html.parser")
    for sel in ("script", "style", "nav", "header", "footer", "aside",
                "noscript", "form", "iframe"):
        for tag in soup.select(sel):
            tag.decompose()

    title = ""
    h2 = soup.find("h2")
    if h2:
        title = h2.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    if not title:
        return None

    # The vote detail block sits under <div class="vote">. Everything
    # outside it is site chrome. Take its full text content.
    vote_div = soup.find("div", class_="vote") or soup.body or soup
    body = vote_div.get_text("\n", strip=True)
    body = re.sub(r"\n{2,}", "\n", body).strip()

    if len(body) < 200:
        return None
    return title, body


def _is_de(url: str) -> bool:
    """Detail URLs without a language prefix are DE; FR/IT/EN sit under /fr|it|en/."""
    path = urlparse(url).path
    if any(s in path for s in SKIP_PATH_SUBSTRINGS):
        return False
    parts = path.lstrip("/").split("/")
    if parts and parts[0] in ("fr", "it", "en"):
        return False
    return path.startswith("/vote/")


def run(limit: int, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    urls = _fetch_index_urls()
    urls = [u for u in urls if _is_de(u)]
    if limit and limit < len(urls):
        urls = urls[:limit]
        logger.info("Limited to first %d URLs.", limit)

    if dry_run:
        logger.info("Sample URLs:")
        for u in urls[:15]:
            logger.info("    %s", u)
        return 0

    today = date.today()
    docs_written = 0
    total_chunks = 0
    skipped = 0

    with Fetcher(rate_limit_seconds=1.0, timeout=20) as fetcher:
        for i, url in enumerate(urls, 1):
            res = fetcher.fetch(url)
            if not res or res.status_code != 200:
                logger.info("skip status=%s %s", res and res.status_code, url)
                skipped += 1
                continue
            extracted = _extract_vote(res.content, url)
            if not extracted:
                logger.info("skip (no body) %s", url)
                skipped += 1
                continue
            title, body = extracted

            doc = Document(
                source_url=res.final_url or url,
                source_name=SOURCE_NAME,
                title=title,
                language=LANGUAGE,
                category=CATEGORY,  # type: ignore[arg-type]
                authority=AUTHORITY,  # type: ignore[arg-type]
                doc_type="reference",  # type: ignore[arg-type]
                text=body,
                entity_name=title,
                entity_type="federal_vote",
                created_at=today,
                updated_at=today,
                ttl_days=TTL_DAYS,
            )
            try:
                chunks: list[Chunk] = chunk_document(doc)
            except Exception as e:
                logger.warning("chunk failed url=%s err=%s", url, e)
                skipped += 1
                continue
            write_chunks(chunks, CHUNKS_ROOT, CATEGORY, SOURCE_SLUG)
            docs_written += 1
            total_chunks += len(chunks)
            if i % 25 == 0:
                logger.info("progress: %d/%d (written=%d)", i, len(urls), docs_written)

    logger.info(
        "Total: docs_written=%d total_chunks=%d skipped=%d",
        docs_written, total_chunks, skipped,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest swissvotes.ch into Phase 1 .jsonl")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap URLs (0 = no cap)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sample URLs; don't fetch")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
