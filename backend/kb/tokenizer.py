"""EmbeddingGemma tokenizer — used in Phase 1 to count tokens only.

Loads the tokenizer from `google/embeddinggemma-300m` (HuggingFace). The
tokenizer file is ~2 MB; no model weights are loaded. Cached in
``~/.cache/huggingface`` after first fetch.

Why the model's own tokenizer and not tiktoken: embedding quality
degrades sharply past EmbeddingGemma's sweet spot (~500 tokens) and
fails past its 2048-token input limit. Using Gemma's tokenizer makes
our Phase-1 token budgets *truth* rather than approximations. See
docs/knowledge_base.md §5.2 and §8.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger("zuribot.kb.tokenizer")

_MODEL_ID = "google/embeddinggemma-300m"


@lru_cache(maxsize=1)
def _tokenizer():
    from tokenizers import Tokenizer

    token = os.getenv("HF_TOKEN")
    try:
        tk = Tokenizer.from_pretrained(_MODEL_ID, auth_token=token) if token else \
             Tokenizer.from_pretrained(_MODEL_ID)
        logger.info("Loaded EmbeddingGemma tokenizer from %s", _MODEL_ID)
        return tk
    except Exception as e:
        raise RuntimeError(
            f"Failed to load EmbeddingGemma tokenizer from '{_MODEL_ID}'. "
            f"Gemma models are gated on HuggingFace — set HF_TOKEN in the "
            f"environment after accepting the model license at "
            f"https://huggingface.co/{_MODEL_ID}. Underlying error: {e}"
        ) from e


def count_tokens(text: str) -> int:
    """Return token count for ``text`` under EmbeddingGemma's tokenizer."""
    if not text:
        return 0
    return len(_tokenizer().encode(text).ids)
