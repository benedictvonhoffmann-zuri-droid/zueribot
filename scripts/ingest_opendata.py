#!/usr/bin/env python3
"""
ZüriBot Open Data Ingestion Script

Fetches dataset descriptions from the Stadt Zürich Open Data portal (CKAN API)
and ingests them into the knowledge base.

This gives ZüriBot awareness of 900+ CC0 datasets — useful for answering
"Is there data about X in Zürich?", pointing users to datasets, and
providing factual city statistics referenced in dataset descriptions.

Usage:
    cd ~/zuribot && source venv/bin/activate
    python scripts/ingest_opendata.py
    python scripts/ingest_opendata.py --limit 100   # first 100 datasets only
    python scripts/ingest_opendata.py --reset        # delete old opendata chunks first
"""

import argparse
import hashlib
import logging
import time
from datetime import date
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_opendata")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = str(PROJECT_ROOT / "data" / "knowledge_base")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "zurich_knowledge"

CKAN_BASE = "https://data.stadt-zuerich.ch/api/3/action"
SOURCE_NAME = "Stadt Zürich Open Data Portal"
CATEGORY = "opendata"


def fetch_package_list() -> list[str]:
    """Fetch all dataset IDs from the CKAN portal."""
    url = f"{CKAN_BASE}/package_list"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError("CKAN package_list call failed")
    return data["result"]


def fetch_package(pkg_id: str) -> dict | None:
    """Fetch metadata for a single dataset."""
    url = f"{CKAN_BASE}/package_show"
    try:
        resp = requests.get(url, params={"id": pkg_id}, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("success"):
            return None
        return data["result"]
    except Exception as e:
        logger.warning(f"  Error fetching {pkg_id}: {e}")
        return None


def build_document_text(pkg: dict) -> str:
    """Convert a CKAN package record to a readable text document."""
    lines = []

    title = pkg.get("title") or pkg.get("name", "")
    notes = pkg.get("notes", "").strip()
    org = pkg.get("organization", {}) or {}
    org_name = org.get("title") or org.get("name", "")
    tags = [t["name"] for t in pkg.get("tags", []) if t.get("name")]
    groups = [g.get("title") or g.get("name", "") for g in pkg.get("groups", [])]
    resources = pkg.get("resources", [])
    resource_formats = list({r.get("format", "") for r in resources if r.get("format")})
    url = pkg.get("url") or f"https://data.stadt-zuerich.ch/dataset/{pkg.get('name', '')}"

    lines.append(f"Datensatz: {title}")
    if org_name:
        lines.append(f"Herausgeber: {org_name}")
    if groups:
        lines.append(f"Kategorien: {', '.join(groups)}")
    if tags:
        lines.append(f"Schlagwörter: {', '.join(tags)}")
    if resource_formats:
        lines.append(f"Formate: {', '.join(resource_formats)}")
    lines.append(f"URL: {url}")
    if notes:
        lines.append("")
        lines.append(notes)

    return "\n".join(lines)


def ingest_package(store, pkg: dict) -> tuple[int, int]:
    """Ingest one CKAN package as a single document. Returns (added, skipped)."""
    from langchain_core.documents import Document

    text = build_document_text(pkg)
    if len(text) < 100:
        return 0, 0

    pkg_id = pkg.get("name", pkg.get("id", "unknown"))
    url = f"https://data.stadt-zuerich.ch/dataset/{pkg_id}"
    title = pkg.get("title") or pkg_id
    chunk_id = hashlib.sha256(f"opendata::{pkg_id}".encode()).hexdigest()

    existing = store._collection.get(ids=[chunk_id])["ids"]
    if existing:
        return 0, 1

    doc = Document(
        page_content=text,
        metadata={
            "source_url": url,
            "source_name": SOURCE_NAME,
            "category": CATEGORY,
            "language": "de",
            "title": title,
            "crawl_date": date.today().isoformat(),
            "depth": 0,
        },
    )
    store.add_documents(documents=[doc], ids=[chunk_id])
    return 1, 0


def main():
    parser = argparse.ArgumentParser(description="Ingest Stadt Zürich Open Data descriptions")
    parser.add_argument("--limit", type=int, default=0, help="Max datasets to ingest (0=all)")
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing opendata chunks before re-ingesting")
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

    # Optionally delete existing opendata chunks
    if args.reset:
        logger.info("Deleting existing opendata chunks ...")
        try:
            existing = store._collection.get(where={"category": CATEGORY})
            if existing["ids"]:
                store._collection.delete(ids=existing["ids"])
                logger.info(f"  Deleted {len(existing['ids'])} existing chunks")
        except Exception as e:
            logger.warning(f"  Could not delete existing chunks: {e}")

    logger.info("Fetching dataset list from data.stadt-zuerich.ch ...")
    pkg_ids = fetch_package_list()
    logger.info(f"Found {len(pkg_ids)} datasets")

    if args.limit:
        pkg_ids = pkg_ids[:args.limit]
        logger.info(f"Limiting to {args.limit} datasets")

    total_added = 0
    total_skipped = 0

    for i, pkg_id in enumerate(pkg_ids):
        pkg = fetch_package(pkg_id)
        if not pkg:
            logger.warning(f"  [{i+1}/{len(pkg_ids)}] Skipped (no data): {pkg_id}")
            continue

        added, skipped = ingest_package(store, pkg)
        total_added += added
        total_skipped += skipped

        if (i + 1) % 50 == 0:
            logger.info(f"  Progress: {i+1}/{len(pkg_ids)} datasets — {total_added} added so far")

        # Polite rate limiting
        time.sleep(0.05)

    logger.info(f"""
=== Open Data ingestion complete ===
Datasets processed:  {len(pkg_ids)}
Chunks added:        {total_added}
Chunks skipped:      {total_skipped}  (duplicates)
Store location:      {STORE_PATH}
""")


if __name__ == "__main__":
    main()
