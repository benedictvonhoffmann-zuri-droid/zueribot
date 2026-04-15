#!/usr/bin/env python3
"""
ZüriBot Wikipedia Ingestion Script

Fetches Wikipedia articles about Zürich (Kreise 1-12, landmarks, districts,
general topics) via the Wikipedia REST API and stores them in the knowledge base.

Usage:
    cd ~/zuribot && source venv/bin/activate
    python scripts/ingest_wikipedia.py
    python scripts/ingest_wikipedia.py --reset    # re-fetch and overwrite

The Wikipedia REST API returns clean plain-text summaries and full article text
without requiring any web scraping or JS rendering.
"""

import argparse
import hashlib
import logging
import time
from datetime import date
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_wikipedia")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = str(PROJECT_ROOT / "data" / "knowledge_base")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "zurich_knowledge"
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200

# Wikipedia article titles to fetch (German Wikipedia)
# Format: (article_title, category_tag)
WIKIPEDIA_ARTICLES = [
    # City overview
    ("Zürich", "neighborhoods"),
    ("Kanton Zürich", "government"),
    ("Geschichte der Stadt Zürich", "neighborhoods"),
    # Stadtkreise 1–12
    ("Stadtkreis Zürich 1", "neighborhoods"),
    ("Stadtkreis Zürich 2", "neighborhoods"),
    ("Stadtkreis Zürich 3", "neighborhoods"),
    ("Stadtkreis Zürich 4", "neighborhoods"),
    ("Stadtkreis Zürich 5", "neighborhoods"),
    ("Stadtkreis Zürich 6", "neighborhoods"),
    ("Stadtkreis Zürich 7", "neighborhoods"),
    ("Stadtkreis Zürich 8", "neighborhoods"),
    ("Stadtkreis Zürich 9", "neighborhoods"),
    ("Stadtkreis Zürich 10", "neighborhoods"),
    ("Stadtkreis Zürich 11", "neighborhoods"),
    ("Stadtkreis Zürich 12", "neighborhoods"),
    # Notable Quartiere
    ("Langstrasse", "neighborhoods"),
    ("Seefeld (Zürich)", "neighborhoods"),
    ("Zürich-West", "neighborhoods"),
    ("Wiedikon", "neighborhoods"),
    ("Wipkingen", "neighborhoods"),
    ("Oerlikon", "neighborhoods"),
    ("Altstetten", "neighborhoods"),
    # Landmarks & geography
    ("Zürichsee", "neighborhoods"),
    ("Limmat", "neighborhoods"),
    ("Uetliberg", "neighborhoods"),
    ("Zürichberg", "neighborhoods"),
    ("Grossmünster", "neighborhoods"),
    ("Fraumünster", "neighborhoods"),
    ("Hauptbahnhof Zürich", "neighborhoods"),
    ("Bahnhofstrasse (Zürich)", "neighborhoods"),
    # Culture & institutions
    ("Kunsthaus Zürich", "neighborhoods"),
    ("Opernhaus Zürich", "neighborhoods"),
    ("Schauspielhaus Zürich", "neighborhoods"),
    ("Schweizerisches Nationalmuseum", "neighborhoods"),
    ("Zoo Zürich", "neighborhoods"),
    ("Tonhalle Zürich", "neighborhoods"),
    # Festivals
    ("Street Parade", "neighborhoods"),
    ("Sechseläuten", "neighborhoods"),
    ("Züri Fäscht", "neighborhoods"),
    ("Zürich Film Festival", "neighborhoods"),
    # Universities
    ("Universität Zürich", "neighborhoods"),
    ("ETH Zürich", "neighborhoods"),
    # Transport
    ("Verkehrsbetriebe Zürich", "neighborhoods"),
    ("S-Bahn Zürich", "neighborhoods"),
    # Practical / Swiss life
    ("Krankenversicherung (Schweiz)", "government"),
    ("Wohnen in der Schweiz", "renting"),
    ("Mietrecht (Schweiz)", "renting"),
]

# English Wikipedia articles (for expat-relevant content)
WIKIPEDIA_ARTICLES_EN = [
    ("Zürich", "neighborhoods"),
    ("Expat life in Switzerland", "guides"),
    ("Swiss German", "neighborhoods"),
]


def _wikipedia_api_get(title: str, lang: str = "de") -> dict | None:
    """Fetch a Wikipedia article via the REST API."""
    encoded = requests.utils.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "ZuriBot/1.0 (https://github.com/zuribot; knowledge base ingestion)"
        })
        if resp.status_code == 404:
            logger.warning(f"  Not found: {title}")
            return None
        if resp.status_code != 200:
            logger.warning(f"  HTTP {resp.status_code} for {title}")
            return None
        return resp.json()
    except Exception as e:
        logger.warning(f"  Error fetching {title}: {e}")
        return None


def _wikipedia_full_text(title: str, lang: str = "de") -> str | None:
    """Fetch full plain-text of a Wikipedia article via the Parsoid API."""
    encoded = requests.utils.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/plain/{encoded}"
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "ZuriBot/1.0 (https://github.com/zuribot; knowledge base ingestion)"
        })
        if resp.status_code != 200:
            return None
        text = resp.text.strip()
        # Remove references section and beyond
        for marker in ["\nLiteratur\n", "\nWeblinks\n", "\nEinzelnachweise\n",
                        "\nSiehe auch\n", "\nReferences\n", "\nExternal links\n"]:
            if marker in text:
                text = text[:text.index(marker)]
        return text if len(text) > 200 else None
    except Exception as e:
        logger.warning(f"  Error fetching full text for {title}: {e}")
        return None


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    import re
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_SIZE_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para if len(para) <= CHUNK_SIZE_CHARS else para[:CHUNK_SIZE_CHARS]
    if current:
        chunks.append(current)
    # Apply overlap
    if len(chunks) > 1:
        import re
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-CHUNK_OVERLAP_CHARS:]
            m = re.search(r"[.!?]\s+", tail)
            if m:
                tail = tail[m.end():]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped
    return chunks


def ingest_article(store, title: str, text: str, url: str,
                   category: str, lang: str) -> tuple[int, int]:
    """Chunk + embed one article. Returns (added, skipped)."""
    from langchain_core.documents import Document
    raw_chunks = chunk_text(text)
    if not raw_chunks:
        return 0, 0

    docs, ids = [], []
    for i, chunk in enumerate(raw_chunks):
        chunk_id = hashlib.sha256(f"wiki::{url}::{i}::{chunk[:80]}".encode()).hexdigest()
        docs.append(Document(
            page_content=chunk,
            metadata={
                "source_url": url,
                "source_name": f"Wikipedia ({lang.upper()})",
                "category": category,
                "language": lang,
                "title": title,
                "crawl_date": date.today().isoformat(),
                "depth": 0,
            },
        ))
        ids.append(chunk_id)

    existing = set(store._collection.get(ids=ids)["ids"])
    new_docs = [d for d, i in zip(docs, ids) if i not in existing]
    new_ids = [i for i in ids if i not in existing]

    if new_docs:
        store.add_documents(documents=new_docs, ids=new_ids)

    return len(new_docs), len(docs) - len(new_docs)


def main():
    parser = argparse.ArgumentParser(description="Ingest Wikipedia articles about Zürich")
    parser.add_argument("--reset", action="store_true", help="Re-fetch all articles (overwrite duplicates)")
    parser.add_argument("--limit", type=int, default=0, help="Max articles to fetch (0=all)")
    args = parser.parse_args()

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    embedding_fn = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    Path(STORE_PATH).mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=STORE_PATH,
        embedding_function=embedding_fn,
    )

    total_added = 0
    total_skipped = 0
    processed = 0

    all_articles = [(t, c, "de") for t, c in WIKIPEDIA_ARTICLES] + \
                   [(t, c, "en") for t, c in WIKIPEDIA_ARTICLES_EN]

    for title, category, lang in all_articles:
        if args.limit and processed >= args.limit:
            break

        logger.info(f"Fetching [{lang}] {title} ...")

        # Try full text first, fall back to summary
        text = _wikipedia_full_text(title, lang=lang)
        if not text:
            data = _wikipedia_api_get(title, lang=lang)
            if data:
                text = data.get("extract", "")
            if not text:
                logger.warning(f"  No content for {title}, skipping")
                continue

        wiki_url = f"https://{lang}.wikipedia.org/wiki/{requests.utils.quote(title.replace(' ', '_'))}"
        added, skipped = ingest_article(store, title, text, wiki_url, category, lang)
        total_added += added
        total_skipped += skipped
        processed += 1
        logger.info(f"  +{added} chunks ({skipped} duplicates)")

        # Polite rate limit
        time.sleep(0.5)

    logger.info(f"""
=== Wikipedia ingestion complete ===
Articles processed:  {processed}
Chunks added:        {total_added}
Chunks skipped:      {total_skipped}  (duplicates)
Store location:      {STORE_PATH}
""")


if __name__ == "__main__":
    main()
