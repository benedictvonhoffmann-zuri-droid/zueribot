"""
Zürich Knowledge Base Connector
- Queries a local Chroma vector store built by scripts/ingest.py
- Multilingual: handles German, Swiss German, English, French, Italian
- Store lives at data/knowledge_base/ (relative to project root)
"""

import logging
from pathlib import Path

logger = logging.getLogger("zuribot.knowledge")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STORE_PATH = str(_PROJECT_ROOT / "data" / "knowledge_base")
_COLLECTION_NAME = "zurich_knowledge"
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Module-level singletons — loaded once on first call, never re-loaded per process
_vectorstore = None


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

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    logger.info("Loading knowledge base embedding model (first call only)...")
    embedding_fn = HuggingFaceEmbeddings(
        model_name=_EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    _vectorstore = Chroma(
        collection_name=_COLLECTION_NAME,
        persist_directory=_STORE_PATH,
        embedding_function=embedding_fn,
    )
    logger.info("Knowledge base loaded.")
    return _vectorstore


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

        return {
            "success": True,
            "data": {
                "query": query,
                "results": chunks,
                "total_chunks_retrieved": len(chunks),
            },
            "source": {"name": "Zürich Knowledge Base", "type": "local-rag"},
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
