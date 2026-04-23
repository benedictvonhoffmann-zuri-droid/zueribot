"""JSONL writer for Phase 1 chunk output.

One file per (category, source) pair. Appends validated Chunk objects
as single-line JSON. Directory layout:

    data/chunks/{category}/{source}/{doc_id}.jsonl

Spec: docs/knowledge_base.md §13.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from backend.kb.metadata import Chunk

logger = logging.getLogger("zuribot.kb.writers")


def write_chunks(
    chunks: Iterable[Chunk],
    root: Path,
    category: str,
    source_slug: str,
) -> Path:
    """Write ``chunks`` for one doc to ``root/category/source_slug/{doc_id}.jsonl``.

    Overwrites any existing file for the same doc_id. Returns the path.
    All chunks must share a doc_id; raises ValueError if not.
    """
    chunks = list(chunks)
    if not chunks:
        raise ValueError("write_chunks called with empty iterable")

    doc_ids = {c.doc_id for c in chunks}
    if len(doc_ids) != 1:
        raise ValueError(f"write_chunks expects one doc_id, got {doc_ids}")
    doc_id = doc_ids.pop()

    out_dir = root / category / source_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{doc_id}.jsonl"

    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.to_jsonl())
            f.write("\n")

    logger.info("Wrote %d chunks for doc %s -> %s", len(chunks), doc_id, path)
    return path
