#!/usr/bin/env python3
"""
ZüriBot Knowledge Base Ingestion Script

Crawls configured sources, chunks text, embeds locally, and stores in Chroma.
Run manually whenever you want to update the knowledge base.

Usage:
    cd ~/zuribot && source venv/bin/activate
    python scripts/ingest.py                    # full crawl
    python scripts/ingest.py --category news    # one category only
    python scripts/ingest.py --reset            # drop store and rebuild
    python scripts/ingest.py --dry-run          # show what would be crawled

Env vars:
    INGEST_RESET=1     same as --reset
    INGEST_LIMIT=5     limit pages per source (for testing)
"""

import argparse
import hashlib
import logging
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = str(PROJECT_ROOT / "data" / "knowledge_base")
MANUAL_CONTENT_PATH = PROJECT_ROOT / "data" / "manual_content"

# ── Embedding + Store ──────────────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "zurich_knowledge"
CHUNK_SIZE_CHARS = 2000   # ~500 tokens for German/English mixed
CHUNK_OVERLAP_CHARS = 200

# ── Rate limiting ──────────────────────────────────────────────────────────
RATE_LIMIT = 1.5  # seconds between requests per domain

# ── Law content filter keywords ────────────────────────────────────────────
LAW_KEYWORDS = [
    "mietrecht", "mietvertrag", "mieter", "vermieter", "kündigung",
    "lärmschutz", "abfall", "parkierung", "baubewilligung",
    "kanton zürich", "stadt zürich", " zh ", "obligationenrecht",
    "wohnungsrecht", "nebenkosten", "kaution",
]

# ── Source Definitions ─────────────────────────────────────────────────────
SOURCES = {
    "government": [
        {"url": "https://www.stadt-zuerich.ch/", "name": "Stadt Zürich", "lang": "de", "depth": 2},
        {"url": "https://www.zh.ch/", "name": "Kanton Zürich", "lang": "de", "depth": 2},
        {"url": "https://www.admin.ch/de", "name": "Schweizer Bundesverwaltung", "lang": "de", "depth": 1},
    ],
    "food": [
        {"url": "https://www.gaultmillau.ch/zueri-isst", "name": "Gault Millau Zürich", "lang": "de", "depth": 2},
        {"url": "https://www.gaultmillau.ch/", "name": "Gault Millau", "lang": "de", "depth": 1},
        {"url": "https://harrysding.ch/", "name": "Harry's Ding", "lang": "de", "depth": 2},
    ],
    "news": [
        {"url": "https://tsri.ch/", "name": "tsri.ch", "lang": "de", "depth": 2},
        {"url": "https://www.srf.ch/", "name": "SRF", "lang": "de", "depth": 1},
    ],
    "law": [
        {"url": "https://www.gesetze.ch/", "name": "Gesetze.ch", "lang": "de", "depth": 2},
        {"url": "https://www.fedlex.admin.ch/de", "name": "Fedlex", "lang": "de", "depth": 2},
    ],
    "renting": [
        {"url": "https://www.hev-schweiz.ch/", "name": "HEV Schweiz", "lang": "de", "depth": 2},
        {"url": "https://www.mieterverband.ch/", "name": "Mieterverband", "lang": "de", "depth": 2},
    ],
}

# ── HTTP Session ───────────────────────────────────────────────────────────
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; ZuriBot/1.0; +https://github.com/zuribot)",
    "Accept-Language": "de,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
})
_last_request_time: dict[str, float] = {}


def _rate_limited_get(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """GET with per-domain rate limiting and graceful error handling."""
    domain = urlparse(url).netloc
    last = _last_request_time.get(domain, 0)
    elapsed = time.time() - last
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)

    try:
        resp = _session.get(url, timeout=timeout, allow_redirects=True)
        _last_request_time[domain] = time.time()
        return resp
    except requests.exceptions.ConnectionError:
        logger.warning(f"  Connection failed: {url}")
    except requests.exceptions.Timeout:
        logger.warning(f"  Timeout: {url}")
    except Exception as e:
        logger.warning(f"  Error fetching {url}: {e}")
    return None


# ── Content Extraction ─────────────────────────────────────────────────────

def extract_text(html: bytes, url: str) -> Optional[tuple[str, str]]:
    """
    Extract (title, main_text) from HTML.
    Returns None if content is too short or not useful.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer",
                      "aside", "form", "iframe", "noscript", "button",
                      "[class*='cookie']", "[class*='banner']", "[class*='ad-']"]):
        tag.decompose()

    # Find main content
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|body", re.I))
        or soup.find(class_=re.compile(r"^(content|main|body|article)", re.I))
        or soup.find("body")
    )
    if not main:
        return None

    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    if len(text) < 300:
        return None

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else url

    return title, text


def is_law_relevant(text: str, url: str) -> bool:
    """For law sites, only keep pages mentioning Zürich-relevant law topics."""
    combined = (text + " " + url).lower()
    return any(kw in combined for kw in LAW_KEYWORDS)


# ── Link Discovery ─────────────────────────────────────────────────────────

def discover_links(html: bytes, base_url: str) -> list[str]:
    """Extract internal links from a page, normalised to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        # Internal links only, no fragments, no files
        if (parsed.netloc == base_domain
                and parsed.scheme in ("http", "https")
                and not parsed.path.endswith((".pdf", ".docx", ".xlsx", ".zip", ".png", ".jpg"))):
            clean = abs_url.split("#")[0].rstrip("/")
            links.append(clean)
    return list(dict.fromkeys(links))  # deduplicate, preserve order


# ── Chunking ───────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks on paragraph/sentence boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_SIZE_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_SIZE_CHARS:
                # Split long paragraph on sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                temp = ""
                for sent in sentences:
                    if len(temp) + len(sent) + 1 <= CHUNK_SIZE_CHARS:
                        temp = (temp + " " + sent).strip()
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = sent
                current = temp
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply overlap
    if len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-CHUNK_OVERLAP_CHARS:]
            m = re.search(r"[.!?]\s+", tail)
            if m:
                tail = tail[m.end():]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped

    return chunks


# ── Store Operations ───────────────────────────────────────────────────────

def build_vectorstore(reset: bool = False):
    """Initialise or open the Chroma store."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    logger.info("(First run downloads ~400 MB to ~/.cache/huggingface/ — subsequent runs are instant)")
    embedding_fn = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    Path(STORE_PATH).mkdir(parents=True, exist_ok=True)

    if reset:
        import chromadb
        client = chromadb.PersistentClient(path=STORE_PATH)
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info("Existing collection deleted (reset mode)")
        except Exception:
            pass

    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=STORE_PATH,
        embedding_function=embedding_fn,
    )
    return store, embedding_fn


def ingest_page(store, url: str, title: str, text: str,
                source_name: str, category: str, language: str, depth: int) -> tuple[int, int]:
    """
    Chunk + embed one page. Returns (chunks_added, chunks_skipped).
    Deduplication: ID = sha256(url + "::" + first 100 chars of chunk).
    """
    from langchain_core.documents import Document

    raw_chunks = chunk_text(text)
    if not raw_chunks:
        return 0, 0

    docs, ids = [], []
    for chunk in raw_chunks:
        chunk_id = hashlib.sha256(f"{url}::{chunk[:100]}".encode()).hexdigest()
        docs.append(Document(
            page_content=chunk,
            metadata={
                "source_url": url,
                "source_name": source_name,
                "category": category,
                "language": language,
                "title": title,
                "crawl_date": date.today().isoformat(),
                "depth": depth,
            },
        ))
        ids.append(chunk_id)

    # Check which IDs already exist
    existing = set(store._collection.get(ids=ids)["ids"])
    new_docs = [d for d, i in zip(docs, ids) if i not in existing]
    new_ids = [i for i in ids if i not in existing]

    if new_docs:
        store.add_documents(documents=new_docs, ids=new_ids)

    return len(new_docs), len(docs) - len(new_docs)


# ── Crawler ────────────────────────────────────────────────────────────────

def crawl_source(store, source: dict, category: str,
                 dry_run: bool = False, limit: int = 0) -> dict:
    """
    Crawl one source definition (BFS up to source['depth']).
    Returns stats dict.
    """
    root_url = source["url"]
    source_name = source["name"]
    language = source["lang"]
    max_depth = source["depth"]

    visited = set()
    queue = [(root_url, 0)]
    stats = {"pages": 0, "chunks_added": 0, "chunks_skipped": 0, "skipped_pages": 0}
    page_count = 0

    while queue:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        if limit and page_count >= limit:
            break

        logger.info(f"  [depth {depth}] {url}")

        if dry_run:
            stats["pages"] += 1
            continue

        resp = _rate_limited_get(url)
        if resp is None:
            stats["skipped_pages"] += 1
            continue

        if resp.status_code in (403, 429, 401):
            logger.warning(f"  Blocked ({resp.status_code}): {url}")
            stats["skipped_pages"] += 1
            continue

        if resp.status_code != 200:
            stats["skipped_pages"] += 1
            continue

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type:
            continue

        extracted = extract_text(resp.content, url)
        if not extracted:
            stats["skipped_pages"] += 1
            continue

        title, text = extracted

        # Law filter
        if category == "law" and not is_law_relevant(text, url):
            logger.info(f"    Skipped (not law-relevant)")
            continue

        added, skipped = ingest_page(
            store, url, title, text, source_name, category, language, depth
        )
        stats["pages"] += 1
        stats["chunks_added"] += added
        stats["chunks_skipped"] += skipped
        page_count += 1

        logger.info(f"    +{added} chunks ({skipped} duplicates)")

        # Queue child links
        if depth < max_depth:
            for link in discover_links(resp.content, url):
                if link not in visited:
                    queue.append((link, depth + 1))

    return stats


# ── Manual Content ─────────────────────────────────────────────────────────

def ingest_manual_content(store, dry_run: bool = False) -> dict:
    """Ingest all .md files from data/manual_content/."""
    stats = {"pages": 0, "chunks_added": 0, "chunks_skipped": 0, "skipped_pages": 0}

    if not MANUAL_CONTENT_PATH.exists():
        return stats

    for md_file in sorted(MANUAL_CONTENT_PATH.glob("*.md")):
        logger.info(f"  {md_file.name}")
        if dry_run:
            stats["pages"] += 1
            continue

        text = md_file.read_text(encoding="utf-8").strip()
        lines = text.split("\n")
        title = lines[0].lstrip("#").strip() if lines else md_file.stem
        body = "\n".join(lines[1:]).strip()

        if not body:
            continue

        # Language from filename suffix
        name = md_file.name.lower()
        lang = "de" if "_de.md" in name else "fr" if "_fr.md" in name else "en"

        # Category from filename
        cat = "general"
        for keyword, cat_name in [
            ("food", "food"), ("restaurant", "food"), ("brunch", "food"),
            ("tram", "transport"), ("transport", "transport"),
            ("recycle", "government"), ("recycling", "government"),
            ("neighborhood", "general"), ("quartier", "general"),
            ("etiquette", "general"), ("custom", "general"),
            ("law", "law"), ("miet", "renting"), ("rent", "renting"),
        ]:
            if keyword in name:
                cat = cat_name
                break

        added, skipped = ingest_page(
            store, f"local://{md_file.name}", title, body,
            "Curated Content", cat, lang, 0
        )
        stats["pages"] += 1
        stats["chunks_added"] += added
        stats["chunks_skipped"] += skipped
        logger.info(f"    +{added} chunks ({skipped} duplicates)")

    return stats


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ZüriBot knowledge base ingestion")
    parser.add_argument("--category", help="Crawl one category only (government|food|news|law|renting|manual)")
    parser.add_argument("--reset", action="store_true", help="Drop and rebuild the store")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be crawled, no changes")
    parser.add_argument("--limit", type=int, default=0, help="Max pages per source (0 = unlimited)")
    args = parser.parse_args()

    reset = args.reset or os.getenv("INGEST_RESET", "0") == "1"
    limit = args.limit or int(os.getenv("INGEST_LIMIT", "0"))

    if args.dry_run:
        logger.info("DRY RUN — no changes will be made")
        store = None
    else:
        store, _ = build_vectorstore(reset=reset)

    totals = {"pages": 0, "chunks_added": 0, "chunks_skipped": 0,
              "sources_ok": 0, "sources_skipped": 0}

    categories = SOURCES.keys() if not args.category or args.category == "manual" else [args.category]

    for category in categories:
        if category not in SOURCES:
            logger.warning(f"Unknown category: {category}")
            continue

        logger.info(f"\n=== Category: {category} ===")
        for source in SOURCES[category]:
            logger.info(f"Source: {source['name']} ({source['url']})")
            stats = crawl_source(store, source, category, dry_run=args.dry_run, limit=limit)
            for k in ("pages", "chunks_added", "chunks_skipped"):
                totals[k] += stats[k]
            if stats["skipped_pages"] and stats["pages"] == 0:
                totals["sources_skipped"] += 1
            else:
                totals["sources_ok"] += 1

    # Manual content
    if not args.category or args.category == "manual":
        logger.info("\n=== Category: manual ===")
        stats = ingest_manual_content(store, dry_run=args.dry_run)
        for k in ("pages", "chunks_added", "chunks_skipped"):
            totals[k] += stats[k]

    logger.info(f"""
=== Ingestion {'(dry run) ' if args.dry_run else ''}complete ===
Pages processed:  {totals['pages']}
Chunks added:     {totals['chunks_added']}
Chunks skipped:   {totals['chunks_skipped']}  (duplicates)
Store location:   {STORE_PATH}
""")


if __name__ == "__main__":
    main()
