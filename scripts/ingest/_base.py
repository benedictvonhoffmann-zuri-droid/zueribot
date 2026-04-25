"""Shared helpers for per-source ingesters.

Keeps individual ingester scripts tight: HTML extraction, paragraph
collection into Sections, procedure/article heuristic, a simple BFS
crawler.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Optional

from bs4 import BeautifulSoup, Tag

from backend.kb.chunker import Document, Section, chunk_document
from backend.kb.fetchers import FetchResult, Fetcher
from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks

logger = logging.getLogger("zuribot.kb.ingest")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_ROOT = PROJECT_ROOT / "data" / "chunks"

_PROCEDURE_HEADING_RE = re.compile(r"\b(schritt|etappe|step|étape|fase)\s*\d", re.IGNORECASE)
_NUMBERED_LIST_RE = re.compile(r"(?m)^\s*\d+[\.\)]\s")


# ── HTML extraction ────────────────────────────────────────────────────────

def extract_title_and_sections(
    html: bytes | str,
    strip_selectors: Iterable[str] = (
        "script", "style", "nav", "header", "footer", "aside",
        "noscript", "form", "iframe",
    ),
    main_selector: str = "main",
) -> tuple[str, list[Section], str]:
    """Return (title, sections, full_text).

    Sections are built by walking h2/h3 headings and collecting paragraphs
    under each until the next heading. If no headings exist, one section
    is emitted with heading='' and the full body text.

    full_text is the concatenated body — useful for procedure heuristics.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Pull a title BEFORE stripping nav/header — some sites (zuerich.com)
    # put the page h1 inside <header>, which would otherwise vanish.
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()
    if not title and soup.title and soup.title.string:
        # Older / hand-built sites (e.g. some Quartierverein WordPress
        # themes) don't render an <h1>. Fall back to the document <title>
        # so we don't drop the page entirely.
        title = soup.title.string.strip()

    # Strip noise tags. We *don't* strip ``form`` here because some legacy
    # sites (some Quartierverein WordPress themes) wrap the entire page —
    # including <main> — in a <form>, so decomposing it nukes the content.
    # Inside-main pruning below handles any stray search/input forms.
    for sel in strip_selectors:
        if sel == "form":
            continue
        for tag in soup.select(sel):
            tag.decompose()

    main = soup.select_one(main_selector) or soup.body or soup
    sections: list[Section] = []
    current_heading = ""
    current_level = 2
    current_paragraphs: list[str] = []

    def flush():
        if current_paragraphs:
            # Dedupe: some sites (e.g. ch.ch) render desktop + mobile copies of
            # the same content in one DOM, which doubles every paragraph.
            seen: set[str] = set()
            uniq = []
            for p in current_paragraphs:
                s = p.strip()
                if s and s not in seen:
                    seen.add(s)
                    uniq.append(s)
            text = "\n\n".join(uniq)
            if text.strip():
                sections.append(Section(
                    heading=current_heading,
                    text=text,
                    level=current_level,
                ))

    for el in main.descendants:
        if not isinstance(el, Tag):
            continue
        name = el.name
        if name in ("h2", "h3"):
            flush()
            current_heading = el.get_text(" ", strip=True)
            current_level = 2 if name == "h2" else 3
            current_paragraphs = []
        elif name in ("p", "li"):
            text = el.get_text(" ", strip=True)
            if text:
                current_paragraphs.append(text)
    flush()

    if not sections:
        body_text = main.get_text("\n", strip=True)
        if body_text:
            sections = [Section(heading="", text=body_text, level=2)]

    full_text = "\n\n".join(s.text for s in sections)
    return title, sections, full_text


def classify_doc_type(full_text: str, headings: list[str]) -> str:
    """Return 'procedure' if the page looks step-shaped, else 'article'."""
    if any(_PROCEDURE_HEADING_RE.search(h) for h in headings if h):
        return "procedure"
    if _NUMBERED_LIST_RE.search(full_text or ""):
        return "procedure"
    return "article"


# ── BFS crawler ────────────────────────────────────────────────────────────

@dataclass
class CrawlConfig:
    seeds: list[str]
    url_prefix: str                 # only URLs starting with this are followed
    max_pages: int = 200
    max_depth: int = 3
    render: bool = True             # True = Playwright, False = plain HTTP
    link_filter: Optional[Callable[[str], bool]] = None


def crawl(fetcher: Fetcher, cfg: CrawlConfig) -> list[FetchResult]:
    """BFS-crawl from ``cfg.seeds`` under ``cfg.url_prefix``. Returns results."""
    seen: set[str] = set()
    frontier: list[tuple[str, int]] = [(u, 0) for u in cfg.seeds]
    results: list[FetchResult] = []

    while frontier and len(results) < cfg.max_pages:
        url, depth = frontier.pop(0)
        if url in seen:
            continue
        seen.add(url)

        fn = fetcher.fetch_rendered if cfg.render else fetcher.fetch
        res = fn(url)
        if res is None or res.status_code != 200:
            logger.info("skip url=%s status=%s", url, res and res.status_code)
            continue

        results.append(res)
        logger.info("crawled %d/%d  %s", len(results), cfg.max_pages, url)

        if depth >= cfg.max_depth:
            continue

        soup = BeautifulSoup(res.content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = f"https://{res.final_url.split('/')[2]}{href}"
            if not href.startswith(cfg.url_prefix):
                continue
            href = href.split("#")[0].rstrip("/")
            if cfg.link_filter and not cfg.link_filter(href):
                continue
            if href not in seen:
                frontier.append((href, depth + 1))

    return results


# ── Document assembly + writing ────────────────────────────────────────────

def make_and_write(
    *,
    category: str,
    source_slug: str,
    source_name: str,
    authority: str,
    language: str,
    results: list[FetchResult],
    title_transform: Optional[Callable[[str, str], str]] = None,
    tags_for: Optional[Callable[[str, str], list[str]]] = None,
    subcategory_for: Optional[Callable[[str], Optional[str]]] = None,
    ttl_days: Optional[int] = None,
) -> dict:
    """Extract, classify, chunk, and write every result. Returns summary dict."""
    today = date.today()
    total_chunks = 0
    docs_written = 0
    procedures = 0
    articles = 0

    for res in results:
        title, sections, full_text = extract_title_and_sections(res.content)
        if not title or len(full_text) < 300:
            logger.info("skip (no content) url=%s", res.url)
            continue
        if title_transform:
            title = title_transform(title, res.url)

        headings = [s.heading for s in sections]
        doc_type = classify_doc_type(full_text, headings)
        if doc_type == "procedure":
            procedures += 1
        else:
            articles += 1

        doc = Document(
            source_url=res.final_url or res.url,
            source_name=source_name,
            title=title,
            language=language,
            category=category,  # type: ignore[arg-type]
            authority=authority,  # type: ignore[arg-type]
            doc_type=doc_type,  # type: ignore[arg-type]
            sections=sections,
            subcategory=subcategory_for(res.url) if subcategory_for else None,
            tags=tags_for(title, full_text) if tags_for else [],
            created_at=today,
            updated_at=today,
            ttl_days=ttl_days,
        )
        body_chars = sum(len(s.text) for s in sections)
        logger.info("chunking url=%s sections=%d chars=%d", res.url, len(sections), body_chars)
        try:
            chunks: list[Chunk] = chunk_document(doc)
        except Exception as e:
            logger.warning("chunk failed url=%s err=%s", res.url, e)
            continue

        write_chunks(chunks, CHUNKS_ROOT, category, source_slug)
        docs_written += 1
        total_chunks += len(chunks)

    return {
        "docs_written": docs_written,
        "total_chunks": total_chunks,
        "procedures": procedures,
        "articles": articles,
    }
