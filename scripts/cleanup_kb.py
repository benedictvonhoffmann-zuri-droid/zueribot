#!/usr/bin/env python3
"""
ZüriBot Knowledge Base Cleanup Script

Removes unwanted chunks from the ChromaDB store:
  1. Non-German language duplicates (chunks from /fr/, /it/, /en/ pages)
  2. Mieterverband chapters for cantons other than MV-general and MV-ZH
     (removes MV-ZG, MV-BE, MV-AG, etc.)

Usage:
    cd ~/zuribot && source venv/bin/activate
    python scripts/cleanup_kb.py --dry-run    # show what would be removed
    python scripts/cleanup_kb.py              # apply cleanup
"""

import argparse
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleanup")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = str(PROJECT_ROOT / "data" / "knowledge_base")
COLLECTION_NAME = "zurich_knowledge"

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Mieterverband canton slugs to remove — keep only '' (general) and 'zh'
# Matched against full source_url. Allowed patterns are checked first (see below),
# so /mv-zh is always safe even though it matches the 2-letter canton pattern.
MV_UNWANTED_PATTERNS = [
    r"mieterverband\.ch/mv-[a-z]{2,3}",  # /mv-ag, /mv-ag/page, etc.
    r"mieterverband\.ch/mieterverband-[a-z]{2,}",
    r"mieterverband\.ch/sektionen/[a-z]{2,3}",
]

# Non-German URL path indicators (these are duplicate content in other languages)
NON_DE_URL_PATTERNS = [
    r"/(fr|it|en|rm)/",          # /fr/, /it/, /en/, /rm/ path segments
    r"/lang/(fr|it|en)/",
    r"\?(lang|language)=(fr|it|en|rm)",
]

# Mieterverband allowed URL patterns — keep pages matching these
MV_ALLOWED_PATTERNS = [
    r"mieterverband\.ch/$",                  # root
    r"mieterverband\.ch/mv-schweiz",         # national/general
    r"mieterverband\.ch/mv-zh",              # Zürich section
    r"mieterverband\.ch/(mietrecht|wohnen|service|ratgeber|news|aktuell|ueber-uns)",
]


def is_non_german_url(url: str) -> bool:
    """Return True if the URL is a non-German language page."""
    return any(re.search(p, url, re.IGNORECASE) for p in NON_DE_URL_PATTERNS)


def is_unwanted_mv(url: str, source_name: str) -> bool:
    """
    Return True if this is a Mieterverband chunk from a non-ZH canton.
    We keep: general MV pages, MV-ZH, top-level content pages.
    We remove: all other cantonal section pages (MV-ZG, MV-BE, etc.).
    """
    if "mieterverband" not in source_name.lower() and "mieterverband.ch" not in url.lower():
        return False

    # If it matches an explicitly allowed pattern, keep it
    for pattern in MV_ALLOWED_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return False

    # If it matches an unwanted canton pattern, remove it
    for pattern in MV_UNWANTED_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True

    # For any Mieterverband URL containing a canton path segment we don't know,
    # log it for review but keep it (conservative default)
    return False


def run_cleanup(dry_run: bool = False) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=STORE_PATH)

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        logger.error(f"Collection '{COLLECTION_NAME}' not found at {STORE_PATH}")
        return

    total = collection.count()
    logger.info(f"Total chunks in store: {total}")

    # Fetch all records (metadata + ids, no embeddings needed)
    batch_size = 5000
    offset = 0
    to_delete: list[str] = []
    non_de_count = 0
    mv_count = 0

    logger.info("Scanning chunks...")

    while True:
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )
        ids = result["ids"]
        metadatas = result["metadatas"]

        if not ids:
            break

        for chunk_id, meta in zip(ids, metadatas):
            url = meta.get("source_url", "")
            source_name = meta.get("source_name", "")

            if is_non_german_url(url):
                to_delete.append(chunk_id)
                non_de_count += 1
                logger.debug(f"  [non-DE] {url}")

            elif is_unwanted_mv(url, source_name):
                to_delete.append(chunk_id)
                mv_count += 1
                logger.debug(f"  [mv-canton] {url}")

        offset += batch_size
        if len(ids) < batch_size:
            break

    logger.info("\nChunks to remove:")
    logger.info(f"  Non-German language duplicates: {non_de_count}")
    logger.info(f"  Unwanted Mieterverband cantons: {mv_count}")
    logger.info(f"  Total to delete: {len(to_delete)}")
    logger.info(f"  Remaining after cleanup: {total - len(to_delete)}")

    if not to_delete:
        logger.info("Nothing to delete.")
        return

    if dry_run:
        logger.info("DRY RUN — no changes made.")
        return

    # Delete in batches (ChromaDB has limits on batch delete size)
    delete_batch = 500
    for i in range(0, len(to_delete), delete_batch):
        batch = to_delete[i:i + delete_batch]
        collection.delete(ids=batch)
        logger.info(f"  Deleted batch {i // delete_batch + 1} ({len(batch)} chunks)")

    remaining = collection.count()
    logger.info(f"\nCleanup complete. Chunks remaining: {remaining}")


def main():
    parser = argparse.ArgumentParser(description="Clean up ZüriBot knowledge base")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be removed without making changes")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN — no changes will be made")

    run_cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
