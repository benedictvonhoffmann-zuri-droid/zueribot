"""Smoke tests for the JSONL writer."""

from __future__ import annotations

import json
from datetime import date

import pytest

from backend.kb.metadata import Chunk
from backend.kb.writers import write_chunks


def _chunk(doc_id: str = "aaa111bbb222", idx: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}_{idx:04d}",
        doc_id=doc_id,
        chunk_index=idx,
        source_url="https://example.ch/x",
        source_name="Example",
        title="Demo",
        heading_path="Example > Demo",
        language="de",
        category="admin",
        authority="federal",
        doc_type="article",
        token_count=10,
        created_at=date(2025, 1, 1),
        updated_at=date(2025, 6, 1),
        display_text="Text.",
        embed_text="Example > Demo\n\nText.",
    )


def test_writes_jsonl_per_doc(tmp_path):
    chunks = [_chunk(idx=i) for i in range(3)]
    out = write_chunks(chunks, tmp_path, "admin", "example")
    assert out.parent == tmp_path / "admin" / "example"
    assert out.name == "aaa111bbb222.jsonl"
    lines = out.read_text().splitlines()
    assert len(lines) == 3
    for line in lines:
        parsed = json.loads(line)
        assert parsed["doc_id"] == "aaa111bbb222"


def test_rejects_empty(tmp_path):
    with pytest.raises(ValueError):
        write_chunks([], tmp_path, "admin", "example")


def test_rejects_mixed_doc_ids(tmp_path):
    chunks = [_chunk("aaa", 0), _chunk("bbb", 1)]
    with pytest.raises(ValueError):
        write_chunks(chunks, tmp_path, "admin", "example")
