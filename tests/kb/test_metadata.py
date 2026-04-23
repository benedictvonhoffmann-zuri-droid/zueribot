"""Smoke tests for the chunk metadata schema + ID helpers."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backend.kb.metadata import (
    SCHEMA_VERSION,
    Chunk,
    make_chunk_id,
    make_doc_id,
)


def _base_kwargs(**overrides):
    base = dict(
        chunk_id="abc123abc123_0001",
        doc_id="abc123abc123",
        chunk_index=1,
        source_url="https://www.ch.ch/de/umzug/",
        source_name="ch.ch",
        title="Umzug",
        heading_path="ch.ch > Wohnen > Umzug",
        language="de",
        category="admin",
        authority="federal",
        doc_type="procedure",
        token_count=123,
        created_at=date(2025, 1, 1),
        updated_at=date(2025, 6, 1),
        display_text="Beim Umzug müssen Sie sich abmelden.",
        embed_text="ch.ch > Wohnen > Umzug\n\nBeim Umzug müssen Sie sich abmelden.",
    )
    base.update(overrides)
    return base


def test_doc_id_is_stable():
    a = make_doc_id("https://ch.ch/de/umzug/", "de")
    b = make_doc_id("https://ch.ch/de/umzug/", "de")
    assert a == b
    assert len(a) == 12


def test_doc_id_differs_by_url_and_language():
    assert make_doc_id("https://a.ch/", "de") != make_doc_id("https://a.ch/", "en")
    assert make_doc_id("https://a.ch/", "de") != make_doc_id("https://b.ch/", "de")


def test_chunk_id_padding():
    assert make_chunk_id("abc", 7) == "abc_0007"
    assert make_chunk_id("abc", "P02") == "abc_P02"


def test_chunk_schema_valid():
    c = Chunk(**_base_kwargs())
    assert c.schema_version == SCHEMA_VERSION
    assert c.chunk_shape == "prose"
    assert c.tags == []


def test_chunk_rejects_bad_subcategory():
    with pytest.raises(ValidationError):
        Chunk(**_base_kwargs(subcategory="Admin/Umzug"))


def test_chunk_rejects_bad_language():
    with pytest.raises(ValidationError):
        Chunk(**_base_kwargs(language="german"))


def test_chunk_rejects_empty_heading_path():
    with pytest.raises(ValidationError):
        Chunk(**_base_kwargs(heading_path=""))


def test_chunk_to_jsonl_is_single_line():
    c = Chunk(**_base_kwargs())
    line = c.to_jsonl()
    assert "\n" not in line
    assert line.startswith("{") and line.endswith("}")
