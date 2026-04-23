"""Chunk metadata schema — pydantic model + ID helpers.

Spec: docs/knowledge_base.md §7 and §9.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = 1

DocType = Literal["article", "procedure", "reference", "statute", "historical"]
ChunkShape = Literal["prose", "table", "list", "code"]
Authority = Literal[
    "federal", "cantonal", "city", "wikipedia", "community", "private",
]
Category = Literal[
    "admin", "housing", "mobility", "health", "emergency", "education",
    "civic", "leisure", "food_drink", "neighborhoods", "law",
]

_SUBCATEGORY_RE = re.compile(r"^[a-z_]+/[a-z0-9_]+$")


def make_doc_id(source_url: str, language: str) -> str:
    """Stable 12-char doc id. Same URL+lang always hashes to the same id."""
    key = f"{source_url}|{language}|{SCHEMA_VERSION}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def make_chunk_id(doc_id: str, chunk_index: int | str) -> str:
    """Zero-padded child chunk id, or passthrough for parent ('P01') ids."""
    if isinstance(chunk_index, str):
        return f"{doc_id}_{chunk_index}"
    return f"{doc_id}_{chunk_index:04d}"


class Chunk(BaseModel):
    """One chunk = one Qdrant point (in Phase 2)."""

    # Identity
    chunk_id: str
    doc_id: str
    chunk_index: int | str  # int for children, "P01"/"P02" for parents
    parent_chunk_id: Optional[str] = None

    # Source
    source_url: str
    source_name: str
    title: str
    heading_path: str

    # Classification
    language: str
    category: Category
    subcategory: Optional[str] = None
    authority: Authority
    doc_type: DocType
    chunk_shape: ChunkShape = "prose"

    # Sizing
    token_count: int = Field(ge=0)

    # Freeform
    tags: list[str] = Field(default_factory=list)

    # Freshness
    created_at: date
    updated_at: date
    ttl_days: Optional[int] = None

    # Schema tracking
    schema_version: int = SCHEMA_VERSION

    # Payload
    display_text: str
    embed_text: str

    # Optional per-doc_type
    step_index: Optional[int] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None
    law_name: Optional[str] = None
    abbrev: Optional[str] = None
    sr_number: Optional[str] = None
    ls_number: Optional[str] = None
    article_number: Optional[str] = None
    paragraph: Optional[str] = None
    period: Optional[str] = None

    # Cross-cutting optional
    district: Optional[str] = None
    license: Optional[str] = None

    @field_validator("subcategory")
    @classmethod
    def _subcategory_shape(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _SUBCATEGORY_RE.match(v):
            raise ValueError(
                f"subcategory must be 'category/leaf' lowercase: {v!r}"
            )
        return v

    @field_validator("language")
    @classmethod
    def _language_is_iso(cls, v: str) -> str:
        if not re.match(r"^[a-z]{2,3}$", v):
            raise ValueError(f"language must be 2-3 letter ISO code: {v!r}")
        return v

    @field_validator("heading_path")
    @classmethod
    def _heading_path_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("heading_path must not be empty (spec §5.5)")
        return v

    def to_jsonl(self) -> str:
        """Single-line JSON serialisation for the Phase 1 .jsonl output."""
        return self.model_dump_json(exclude_none=False)
