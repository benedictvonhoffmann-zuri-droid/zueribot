"""Knowledge base Phase 1 pipeline — crawl, chunk, emit .jsonl.

Spec: docs/knowledge_base.md.

No embedding, no vector DB writes here. Phase 2 (AI pod) consumes the
.jsonl output, embeds with EmbeddingGemma-300M, upserts into Qdrant.
"""

from backend.kb.metadata import Chunk, make_chunk_id, make_doc_id
from backend.kb.tokenizer import count_tokens

__all__ = ["Chunk", "make_chunk_id", "make_doc_id", "count_tokens"]
