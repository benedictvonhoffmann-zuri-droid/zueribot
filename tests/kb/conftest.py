"""Shared fixtures — stub the tokenizer so tests run without HF access.

Real token counts vary with the model's tokenizer. For structure-level
tests we only need a deterministic, reasonable approximation. We use a
whitespace-word count (multiplied for German compound words) as a
stand-in. Integration tests that actually need the Gemma tokenizer
should set HF_TOKEN and call ``count_tokens`` directly.
"""

from __future__ import annotations

import pytest


def _fake_count(text: str) -> int:
    # ~1.3 tokens per whitespace-word is a reasonable DE/EN average.
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3) or 1


@pytest.fixture(autouse=True)
def _stub_tokenizer(monkeypatch):
    monkeypatch.setattr(
        "backend.kb.tokenizer.count_tokens", _fake_count, raising=True,
    )
    monkeypatch.setattr(
        "backend.kb.chunker.count_tokens", _fake_count, raising=True,
    )
