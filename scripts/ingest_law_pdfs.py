#!/usr/bin/env python3
"""
ZüriBot Law PDF Ingestion Script

Ingests manually downloaded Swiss federal law PDFs into a SEPARATE
ChromaDB collection ("zurich_laws"), distinct from the general knowledge base.

This collection is only queried when the user explicitly asks about law
(see tools/search_knowledge_base.py, category filter "law_pdf").

Usage:
    cd ~/zuribot && source venv/bin/activate

    # Place your PDFs in data/law_pdfs/ with filenames like:
    #   bundesverfassung.pdf
    #   obligationenrecht.pdf
    #   zgb.pdf
    #   strafgesetzbuch.pdf
    #   strafprozessordnung.pdf
    #   zpo.pdf

    python scripts/ingest_law_pdfs.py               # ingest all PDFs in data/law_pdfs/
    python scripts/ingest_law_pdfs.py --dry-run      # preview what would be ingested
    python scripts/ingest_law_pdfs.py --reset        # drop and rebuild law collection

Fedlex download links (save as PDF):
    Bundesverfassung:         https://www.fedlex.admin.ch/eli/cc/1999/404/de
    Obligationenrecht (OR):   https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de
    ZGB:                      https://www.fedlex.admin.ch/eli/cc/24/233_245_233/de
    Strafgesetzbuch (StGB):   https://www.fedlex.admin.ch/eli/cc/54/757_781_799/de
    Strafprozessordnung:      https://www.fedlex.admin.ch/eli/cc/2010/267/de
    ZPO:                      https://www.fedlex.admin.ch/eli/cc/2010/262/de
    Anforderungen Fahrzeuge:  https://www.fedlex.admin.ch/eli/cc/1995/4425_4425_4425/de
    Verkehrsregelnverordnung: https://www.fedlex.admin.ch/eli/cc/1963/741_763_779/de

    On each fedlex page, click "PDF" in the top-right to download the current version.
"""

import argparse
import hashlib
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("law_ingest")

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAW_PDF_PATH = PROJECT_ROOT / "data" / "law_pdfs"
LAW_STORE_PATH = str(PROJECT_ROOT / "data" / "law_knowledge_base")

# ── Embedding + Store ──────────────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LAW_COLLECTION_NAME = "zurich_laws"
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 300  # larger overlap for legal text — articles span chunks

# ── Known law metadata (filename stem → metadata) ─────────────────────────
LAW_METADATA = {
    "bundesverfassung":       {"name": "Bundesverfassung (BV)", "sr": "101",      "abbrev": "BV"},
    "bv":                     {"name": "Bundesverfassung (BV)", "sr": "101",      "abbrev": "BV"},
    "obligationenrecht":      {"name": "Obligationenrecht (OR)", "sr": "220",     "abbrev": "OR"},
    "or":                     {"name": "Obligationenrecht (OR)", "sr": "220",     "abbrev": "OR"},
    "zgb":                    {"name": "Zivilgesetzbuch (ZGB)", "sr": "210",      "abbrev": "ZGB"},
    "zivilgesetzbuch":        {"name": "Zivilgesetzbuch (ZGB)", "sr": "210",      "abbrev": "ZGB"},
    "strafgesetzbuch":        {"name": "Strafgesetzbuch (StGB)", "sr": "311.0",   "abbrev": "StGB"},
    "stgb":                   {"name": "Strafgesetzbuch (StGB)", "sr": "311.0",   "abbrev": "StGB"},
    "strafprozessordnung":    {"name": "Strafprozessordnung (StPO)", "sr": "312.0", "abbrev": "StPO"},
    "stpo":                   {"name": "Strafprozessordnung (StPO)", "sr": "312.0", "abbrev": "StPO"},
    "zpo":                    {"name": "Zivilprozessordnung (ZPO)", "sr": "272",  "abbrev": "ZPO"},
    "zivilprozessordnung":    {"name": "Zivilprozessordnung (ZPO)", "sr": "272",  "abbrev": "ZPO"},
    "anforderungen_fahrzeuge":{"name": "Verordnung Anforderungen Fahrzeuge", "sr": "741.41", "abbrev": "VTS"},
    "verkehrsregelnverordnung":{"name": "Verkehrsregelnverordnung (VRV)", "sr": "741.11", "abbrev": "VRV"},
    "vrv":                    {"name": "Verkehrsregelnverordnung (VRV)", "sr": "741.11", "abbrev": "VRV"},
}


def extract_pdf_text(pdf_path: Path) -> tuple[str, int]:
    """
    Extract text from a PDF using pypdf.
    Returns (full_text, page_count).
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("pypdf not installed. Run: pip install pypdf")
        sys.exit(1)

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    pages_text = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            # Clean up common PDF extraction artefacts
            text = re.sub(r"-\n(\w)", r"\1", text)    # hyphenated line breaks
            text = re.sub(r"(\w)\n(\w)", r"\1 \2", text)  # mid-sentence line breaks
            text = re.sub(r"\n{3,}", "\n\n", text)     # excessive blank lines
            text = text.strip()
            if text and not _is_index_page(text):
                pages_text.append(f"[Seite {i + 1}]\n{text}")
        except Exception as e:
            logger.warning(f"  Could not extract page {i + 1}: {e}")

    return "\n\n".join(pages_text), page_count


def _is_index_page(text: str) -> bool:
    """
    Return True if this page looks like a table of contents, footnote list,
    or amendment log rather than actual article text.
    Heuristic: most lines are short (< 6 words) AND contain "Art." or
    are purely numeric (footnote references like "AS 2011 891").
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 4:
        return False
    short_lines = sum(1 for l in lines if len(l.split()) < 6)
    art_refs = sum(1 for l in lines if re.match(r"^(Art\.|§|\d+\.?\s|AS \d|SR \d|BBl )", l))
    # If >70% of lines are short AND >40% look like index references → skip
    return (short_lines / len(lines) > 0.70) and (art_refs / len(lines) > 0.40)


def chunk_legal_text(text: str) -> list[str]:
    """
    Chunk legal text, preferring to break at article boundaries (Art. X / § X).
    Falls back to paragraph boundaries.
    """
    # Try to split on article markers first
    article_pattern = re.compile(
        r"(?=\n(?:Art\.|§|Artikel|Abschnitt|Kapitel|Titel)\s*\d+)",
        re.MULTILINE
    )
    articles = article_pattern.split(text)

    chunks = []
    current = ""

    for article in articles:
        article = article.strip()
        if not article:
            continue

        if len(current) + len(article) + 2 <= CHUNK_SIZE_CHARS:
            current = (current + "\n\n" + article).strip()
        else:
            if current:
                chunks.append(current)
            if len(article) > CHUNK_SIZE_CHARS:
                # Fall back to paragraph splitting for very long articles
                paragraphs = [p.strip() for p in article.split("\n\n") if p.strip()]
                temp = ""
                for para in paragraphs:
                    if len(temp) + len(para) + 2 <= CHUNK_SIZE_CHARS:
                        temp = (temp + "\n\n" + para).strip()
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = para
                current = temp
            else:
                current = article

    if current:
        chunks.append(current)

    # Apply overlap (carry tail of previous chunk into next)
    if len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-CHUNK_OVERLAP_CHARS:]
            # Try to start overlap at a sentence boundary
            m = re.search(r"[.!?]\s+", tail)
            if m:
                tail = tail[m.end():]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped

    return chunks


def build_law_vectorstore(reset: bool = False):
    """Initialise or open the law-specific Chroma store."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    embedding_fn = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    Path(LAW_STORE_PATH).mkdir(parents=True, exist_ok=True)

    if reset:
        import chromadb
        client = chromadb.PersistentClient(path=LAW_STORE_PATH)
        try:
            client.delete_collection(LAW_COLLECTION_NAME)
            logger.info("Existing law collection deleted (reset mode)")
        except Exception:
            pass

    store = Chroma(
        collection_name=LAW_COLLECTION_NAME,
        persist_directory=LAW_STORE_PATH,
        embedding_function=embedding_fn,
    )
    return store


def ingest_pdf(store, pdf_path: Path, dry_run: bool = False) -> dict:
    """Ingest a single PDF into the law store."""
    from langchain_core.documents import Document

    stem = pdf_path.stem.lower().replace(" ", "_").replace("-", "_")
    meta_override = LAW_METADATA.get(stem, {})

    law_name = meta_override.get("name", pdf_path.stem)
    sr_number = meta_override.get("sr", "")
    abbrev = meta_override.get("abbrev", pdf_path.stem.upper())

    logger.info(f"  {pdf_path.name} → {law_name} (SR {sr_number})")

    if dry_run:
        return {"chunks_added": 0, "chunks_skipped": 0, "pages": 0}

    text, page_count = extract_pdf_text(pdf_path)
    if not text.strip():
        logger.warning(f"  No text extracted from {pdf_path.name}")
        return {"chunks_added": 0, "chunks_skipped": 0, "pages": 0}

    logger.info(f"  Extracted {len(text)} chars from {page_count} pages")

    chunks = chunk_legal_text(text)
    logger.info(f"  Split into {len(chunks)} chunks")

    docs, ids = [], []
    seen_ids: set[str] = set()

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.sha256(f"{pdf_path.name}::{i}::{chunk[:100]}".encode()).hexdigest()
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)

        docs.append(Document(
            page_content=chunk,
            metadata={
                "source_file": pdf_path.name,
                "law_name": law_name,
                "sr_number": sr_number,
                "abbrev": abbrev,
                "category": "law_pdf",
                "language": "de",
                "crawl_date": date.today().isoformat(),
            },
        ))
        ids.append(chunk_id)

    if not docs:
        return {"chunks_added": 0, "chunks_skipped": 0, "pages": page_count}

    existing = set(store._collection.get(ids=ids)["ids"])
    new_docs = [d for d, i in zip(docs, ids) if i not in existing]
    new_ids = [i for i in ids if i not in existing]
    skipped = len(docs) - len(new_docs)

    if new_docs:
        store.add_documents(documents=new_docs, ids=new_ids)

    return {"chunks_added": len(new_docs), "chunks_skipped": skipped, "pages": page_count}


def main():
    parser = argparse.ArgumentParser(description="ZüriBot law PDF ingestion")
    parser.add_argument("--reset", action="store_true", help="Drop and rebuild the law store")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested, no changes")
    parser.add_argument("files", nargs="*", help="Specific PDF files to ingest (default: all in data/law_pdfs/)")
    args = parser.parse_args()

    if not LAW_PDF_PATH.exists():
        LAW_PDF_PATH.mkdir(parents=True)
        logger.info(f"Created {LAW_PDF_PATH} — place your law PDFs here and re-run.")
        return

    if args.files:
        pdf_files = [Path(f) for f in args.files]
    else:
        pdf_files = sorted(LAW_PDF_PATH.glob("*.pdf"))

    if not pdf_files:
        logger.info(f"No PDFs found in {LAW_PDF_PATH}")
        logger.info("Download PDFs from fedlex.admin.ch and place them there.")
        return

    if args.dry_run:
        logger.info("DRY RUN — no changes will be made")
        for f in pdf_files:
            logger.info(f"  Would ingest: {f.name}")
        return

    store = build_law_vectorstore(reset=args.reset)
    totals = {"chunks_added": 0, "chunks_skipped": 0, "pages": 0}

    for pdf_path in pdf_files:
        if not pdf_path.exists():
            logger.warning(f"File not found: {pdf_path}")
            continue
        stats = ingest_pdf(store, pdf_path)
        logger.info(f"    +{stats['chunks_added']} chunks ({stats['chunks_skipped']} duplicates)")
        for k in totals:
            totals[k] += stats[k]

    import chromadb
    client = chromadb.PersistentClient(path=LAW_STORE_PATH)
    collection_size = client.get_collection(LAW_COLLECTION_NAME).count()

    logger.info(f"""
=== Law PDF ingestion complete ===
PDFs processed:   {len(pdf_files)}
Pages processed:  {totals['pages']}
Chunks added:     {totals['chunks_added']}
Chunks skipped:   {totals['chunks_skipped']}  (duplicates)
Collection size:  {collection_size} chunks
Store location:   {LAW_STORE_PATH}
""")


if __name__ == "__main__":
    main()
