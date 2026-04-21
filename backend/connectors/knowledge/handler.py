"""Knowledge base connector — local Chroma vector stores (general + Swiss law)."""

import logging
import re
from pathlib import Path

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.knowledge")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_STORE_PATH = str(_PROJECT_ROOT / "data" / "knowledge_base")
_COLLECTION_NAME = "zurich_knowledge"
_LAW_STORE_PATH = str(_PROJECT_ROOT / "data" / "law_knowledge_base")
_LAW_COLLECTION_NAME = "zurich_laws"
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class KnowledgeConnector(BaseConnector):
    manifest = manifest

    _vectorstore = None
    _law_vectorstore = None
    _embedding_fn = None

    def _get_embedding_fn(self):
        if KnowledgeConnector._embedding_fn is not None:
            return KnowledgeConnector._embedding_fn
        from langchain_huggingface import HuggingFaceEmbeddings
        logger.info("Loading knowledge base embedding model (first call only)...")
        KnowledgeConnector._embedding_fn = HuggingFaceEmbeddings(
            model_name=_EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        return KnowledgeConnector._embedding_fn

    def _get_vectorstore(self):
        if KnowledgeConnector._vectorstore is not None:
            return KnowledgeConnector._vectorstore

        store_path = Path(_STORE_PATH)
        if not store_path.exists() or not any(store_path.iterdir()):
            raise FileNotFoundError(
                f"Knowledge base not found at {_STORE_PATH}. Run: python scripts/ingest.py"
            )

        from langchain_chroma import Chroma
        KnowledgeConnector._vectorstore = Chroma(
            collection_name=_COLLECTION_NAME,
            persist_directory=_STORE_PATH,
            embedding_function=self._get_embedding_fn(),
        )
        logger.info("General knowledge base loaded.")
        return KnowledgeConnector._vectorstore

    def _get_law_vectorstore(self):
        if KnowledgeConnector._law_vectorstore is not None:
            return KnowledgeConnector._law_vectorstore

        store_path = Path(_LAW_STORE_PATH)
        if not store_path.exists() or not any(store_path.iterdir()):
            raise FileNotFoundError(
                f"Law knowledge base not found at {_LAW_STORE_PATH}. Run: python scripts/ingest_law_pdfs.py"
            )

        from langchain_chroma import Chroma
        KnowledgeConnector._law_vectorstore = Chroma(
            collection_name=_LAW_COLLECTION_NAME,
            persist_directory=_LAW_STORE_PATH,
            embedding_function=self._get_embedding_fn(),
        )
        logger.info("Law knowledge base loaded.")
        return KnowledgeConnector._law_vectorstore

    def search_knowledge_base(self, query: str, limit: int = 5) -> dict:
        try:
            store = self._get_vectorstore()
            results = store.similarity_search_with_score(query, k=limit)

            if not results:
                return self.ok({
                    "query": query,
                    "results": [],
                    "message": "No relevant knowledge found. Try rephrasing or use web_search.",
                })

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

            return self.ok({
                "query": query,
                "results": chunks,
                "total_chunks_retrieved": len(chunks),
                "sources": sources,
            })
        except FileNotFoundError as e:
            return self.err(e)
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}", exc_info=True)
            return self.err(f"Knowledge base error: {str(e)}")

    def search_law_knowledge_base(self, query: str, limit: int = 5) -> dict:
        try:
            store = self._get_law_vectorstore()

            art_match = re.search(r"(?:Art(?:ikel)?\.?\s*|§\s*)(\d+[a-z]?)\b", query, re.IGNORECASE)
            if art_match:
                art_num = art_match.group(1)
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

                import chromadb as _chromadb
                raw_client = _chromadb.PersistentClient(path=_LAW_STORE_PATH)
                raw_collection = raw_client.get_collection(_LAW_COLLECTION_NAME)
                total = raw_collection.count()
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
                        return self.ok({
                            "query": query,
                            "results": chunks[:limit],
                            "total_chunks_retrieved": len(chunks[:limit]),
                        })

            results = store.similarity_search_with_score(query, k=limit * 5)

            if not results:
                return self.ok({
                    "query": query,
                    "results": [],
                    "message": "No matching law articles found.",
                })

            chunks = []
            for doc, score in results:
                text = doc.page_content
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if len(lines) > 4:
                    avg_words = sum(len(l.split()) for l in lines) / len(lines)
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

            return self.ok({
                "query": query,
                "results": chunks,
                "total_chunks_retrieved": len(chunks),
            })
        except FileNotFoundError as e:
            return self.err(e)
        except Exception as e:
            logger.error(f"Law knowledge base search failed: {e}", exc_info=True)
            return self.err(f"Law knowledge base error: {str(e)}")
