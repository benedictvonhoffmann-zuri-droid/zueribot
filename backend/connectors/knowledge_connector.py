"""
Zürich Knowledge Base Connector
- Queries a local Chroma vector store built by scripts/ingest.py
- Multilingual: handles German, Swiss German, English, French, Italian
- General store lives at data/knowledge_base/ (relative to project root)
- Law PDF store lives at data/law_knowledge_base/ (built by scripts/ingest_law_pdfs.py)
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger("zuribot.knowledge")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STORE_PATH = str(_PROJECT_ROOT / "data" / "knowledge_base")
_COLLECTION_NAME = "zurich_knowledge"
_LAW_STORE_PATH = str(_PROJECT_ROOT / "data" / "law_knowledge_base")
_LAW_COLLECTION_NAME = "zurich_laws"
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Module-level singletons — loaded once on first call, never re-loaded per process
_vectorstore = None
_law_vectorstore = None
_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn
    from langchain_huggingface import HuggingFaceEmbeddings
    logger.info("Loading knowledge base embedding model (first call only)...")
    _embedding_fn = HuggingFaceEmbeddings(
        model_name=_EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embedding_fn


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    store_path = Path(_STORE_PATH)
    if not store_path.exists() or not any(store_path.iterdir()):
        raise FileNotFoundError(
            f"Knowledge base not found at {_STORE_PATH}. "
            "Run: python scripts/ingest.py"
        )

    from langchain_chroma import Chroma
    _vectorstore = Chroma(
        collection_name=_COLLECTION_NAME,
        persist_directory=_STORE_PATH,
        embedding_function=_get_embedding_fn(),
    )
    logger.info("General knowledge base loaded.")
    return _vectorstore


def _get_law_vectorstore():
    global _law_vectorstore
    if _law_vectorstore is not None:
        return _law_vectorstore

    store_path = Path(_LAW_STORE_PATH)
    if not store_path.exists() or not any(store_path.iterdir()):
        raise FileNotFoundError(
            f"Law knowledge base not found at {_LAW_STORE_PATH}. "
            "Run: python scripts/ingest_law_pdfs.py"
        )

    from langchain_chroma import Chroma
    _law_vectorstore = Chroma(
        collection_name=_LAW_COLLECTION_NAME,
        persist_directory=_LAW_STORE_PATH,
        embedding_function=_get_embedding_fn(),
    )
    logger.info("Law knowledge base loaded.")
    return _law_vectorstore


def search_knowledge_base(query: str, limit: int = 5) -> dict:
    """
    Search the Zürich knowledge base for cultural, local, and legal information.

    Args:
        query: Natural language question or topic (any supported language)
        limit: Number of chunks to retrieve (default 5)

    Returns:
        Standard ZüriBot connector response dict
    """
    try:
        store = _get_vectorstore()
        results = store.similarity_search_with_score(query, k=limit)

        if not results:
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": [],
                    "message": "No relevant knowledge found. Try rephrasing or use web_search.",
                },
                "source": {"name": "Zürich Knowledge Base", "type": "local-rag"},
                "error": None,
            }

        chunks = []
        for doc, score in results:
            chunks.append({
                "text": doc.page_content,
                "score": round(float(score), 4),
                "source_url": doc.metadata.get("source_url", ""),
                "source_name": doc.metadata.get("source_name", ""),
                "language": doc.metadata.get("language", ""),
                "category": doc.metadata.get("category", ""),
                "title": doc.metadata.get("title", ""),
            })

        # Build a deduplicated list of actual sources for citation
        seen = set()
        sources = []
        for c in chunks:
            key = c["source_name"]
            if key and key not in seen:
                seen.add(key)
                entry = {"name": c["source_name"]}
                url = c.get("source_url", "")
                if url and not url.startswith("local://"):
                    entry["url"] = url
                sources.append(entry)

        return {
            "success": True,
            "data": {
                "query": query,
                "results": chunks,
                "total_chunks_retrieved": len(chunks),
                "sources": sources,  # Cite these in your answer
            },
            "source": {
                "name": ", ".join(s["name"] for s in sources) or "Zürich Knowledge Base",
                "type": "local-rag",
            },
            "error": None,
        }

    except FileNotFoundError as e:
        return {
            "success": False,
            "data": None,
            "source": {"name": "Zürich Knowledge Base", "type": "local-rag"},
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "source": {"name": "Zürich Knowledge Base", "type": "local-rag"},
            "error": f"Knowledge base error: {str(e)}",
        }


def search_law_knowledge_base(query: str, limit: int = 5) -> dict:
    """
    Search the Swiss law knowledge base (federal statutes as PDFs).

    Use this tool ONLY when the user explicitly asks about specific legal articles,
    statutory text, rights and obligations under Swiss law, or citations.
    Do NOT use for general renting tips or advice — use search_knowledge_base instead.

    Args:
        query: Legal question or article reference (e.g. "OR Art. 271 Kündigung", "ZGB Eigentumsrecht")
        limit: Number of chunks to retrieve (default 5)

    Returns:
        Standard ZüriBot connector response dict
    """
    try:
        store = _get_law_vectorstore()

        # For specific article number lookups (e.g. "OR Art. 271"), do a keyword scan
        # of all OR/ZGB/etc. chunks first — embedding similarity can't find exact article
        # numbers reliably in a large corpus.
        art_match = re.search(r"(?:Art(?:ikel)?\.?\s*|§\s*)(\d+[a-z]?)\b", query, re.IGNORECASE)
        if art_match:
            art_num = art_match.group(1)
            # Detect law abbreviation in query to filter results to the right statute
            LAW_ABBREV_MAP = {
                "or": "OBLIGATIONENRECHT", "obligationenrecht": "OBLIGATIONENRECHT",
                "zgb": "ZIVILGESETZBUCH", "zivilgesetzbuch": "ZIVILGESETZBUCH",
                "bv": "BUNDESVERFASSUNG", "bundesverfassung": "BUNDESVERFASSUNG",
                "stgb": "STRAFGESETZBUCH", "strafgesetzbuch": "STRAFGESETZBUCH",
                "stpo": "STRAFPROZESSORDNUNG", "strafprozessordnung": "STRAFPROZESSORDNUNG",
                "zpo": "ZIVILPROZESSORDNUNG", "zivilprozessordnung": "ZIVILPROZESSORDNUNG",
                "vrv": "VRV", "verkehrsregeln": "VRV",
            }
            target_law = None
            query_lower = query.lower()
            for abbrev, law_fragment in LAW_ABBREV_MAP.items():
                if abbrev in query_lower.split() or f" {abbrev}" in query_lower or query_lower.startswith(abbrev):
                    target_law = law_fragment
                    break

            # Keyword scan: fetch all docs and filter by article number presence
            import chromadb as _chromadb
            raw_client = _chromadb.PersistentClient(path=_LAW_STORE_PATH)
            raw_collection = raw_client.get_collection(_LAW_COLLECTION_NAME)
            total = raw_collection.count()
            # Scan in batches for "Art. {num}" pattern
            art_pattern = re.compile(rf"\bArt\.\s*{re.escape(art_num)}\b", re.IGNORECASE)
            keyword_hits = []
            for offset in range(0, min(total, 10000), 2000):
                batch = raw_collection.get(limit=2000, offset=offset, include=["documents", "metadatas"])
                for doc_text, meta in zip(batch["documents"], batch["metadatas"]):
                    if target_law and target_law not in meta.get("law_name", "").upper():
                        continue
                    if art_pattern.search(doc_text):
                        keyword_hits.append((doc_text, meta))
            if keyword_hits:
                # Return keyword matches directly (already filtered by article number)
                chunks = []
                for doc_text, meta in keyword_hits[:limit]:
                    lines = [l.strip() for l in doc_text.split("\n") if l.strip()]
                    if len(lines) > 4:
                        avg_words = sum(len(l.split()) for l in lines) / len(lines)
                        footnote_lines = sum(1 for l in lines if re.search(r"\d{3,}\s+AS \d{4}", l))
                        if avg_words < 5 or footnote_lines / len(lines) > 0.3:
                            continue
                    chunks.append({
                        "text": doc_text,
                        "score": 1.0,
                        "law_name": meta.get("law_name", ""),
                        "abbrev": meta.get("abbrev", ""),
                        "sr_number": meta.get("sr_number", ""),
                        "source_file": meta.get("source_file", ""),
                    })
                if chunks:
                    return {
                        "success": True,
                        "data": {"query": query, "results": chunks[:limit], "total_chunks_retrieved": len(chunks[:limit])},
                        "source": {"name": "Swiss Law (Fedlex PDFs)", "type": "local-rag"},
                        "error": None,
                    }

        # Fetch more candidates than needed so TOC chunks can be filtered out
        results = store.similarity_search_with_score(query, k=limit * 5)

        if not results:
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": [],
                    "message": "No matching law articles found.",
                },
                "source": {"name": "Swiss Law (Fedlex PDFs)", "type": "local-rag"},
                "error": None,
            }

        chunks = []
        for doc, score in results:
            text = doc.page_content
            # Skip index/TOC/footnote chunks — they have no usable article text.
            # These look like:
            #   "Art. 247\nF. Aufhebung...\nArt. 248\n..." (TOC)
            #   "1019  AS 2011 891\n1020  AS 2011 891\n..." (amendment footnotes)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) > 4:
                avg_words = sum(len(l.split()) for l in lines) / len(lines)
                # Amendment footnote pattern: "1019  AS 2011 891" or "1019 AS 2011 891"
                footnote_lines = sum(1 for l in lines if re.search(r"\d{3,}\s+AS \d{4}", l))
                if avg_words < 5 or footnote_lines / len(lines) > 0.3:
                    continue
            chunks.append({
                "text": text,
                "score": round(float(score), 4),
                "law_name": doc.metadata.get("law_name", ""),
                "abbrev": doc.metadata.get("abbrev", ""),
                "sr_number": doc.metadata.get("sr_number", ""),
                "source_file": doc.metadata.get("source_file", ""),
            })
            if len(chunks) >= limit:
                break

        return {
            "success": True,
            "data": {
                "query": query,
                "results": chunks,
                "total_chunks_retrieved": len(chunks),
            },
            "source": {"name": "Swiss Law (Fedlex PDFs)", "type": "local-rag"},
            "error": None,
        }

    except FileNotFoundError as e:
        return {
            "success": False,
            "data": None,
            "source": {"name": "Swiss Law (Fedlex PDFs)", "type": "local-rag"},
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Law knowledge base search failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "source": {"name": "Swiss Law (Fedlex PDFs)", "type": "local-rag"},
            "error": f"Law knowledge base error: {str(e)}",
        }
