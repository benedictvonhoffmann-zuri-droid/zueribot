"""Smoke tests for chunker behaviour across doc_types."""

from __future__ import annotations

from datetime import date

import pytest

from backend.kb.chunker import Document, Section, chunk_document


def _base_doc(**overrides) -> Document:
    base = dict(
        source_url="https://example.ch/x",
        source_name="Example",
        title="Demo",
        language="de",
        category="admin",
        authority="federal",
        doc_type="article",
        created_at=date(2025, 1, 1),
        updated_at=date(2025, 6, 1),
    )
    base.update(overrides)
    return Document(**base)


_LOREM = (
    "Die Schweiz ist ein föderaler Bundesstaat. Sie besteht aus 26 Kantonen. "
    "Zürich ist der bevölkerungsreichste Kanton. "
)


def test_article_produces_valid_chunks():
    doc = _base_doc(sections=[Section("Übersicht", _LOREM * 50, 2)])
    chunks = chunk_document(doc)
    assert chunks, "chunker produced zero chunks"
    for c in chunks:
        assert c.doc_type == "article"
        assert "Example > Demo" in c.heading_path
        assert c.embed_text.startswith(c.heading_path)
        assert c.token_count > 0


def test_article_parent_child_emitted_for_long_sections():
    # One huge section should trigger a parent chunk.
    huge = _LOREM * 200
    doc = _base_doc(sections=[Section("Dossier", huge, 2)])
    chunks = chunk_document(doc)
    parents = [c for c in chunks if isinstance(c.chunk_index, str) and c.chunk_index.startswith("P")]
    children_with_parent = [c for c in chunks if c.parent_chunk_id]
    assert parents, "expected at least one parent chunk"
    assert children_with_parent, "expected at least one child linked to parent"
    assert children_with_parent[0].parent_chunk_id == parents[0].chunk_id


def test_reference_never_splits():
    doc = _base_doc(
        doc_type="reference",
        text=_LOREM * 100,
        entity_name="USZ",
        entity_type="hospital",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].entity_name == "USZ"


def test_procedure_whole_when_short():
    doc = _base_doc(doc_type="procedure", text=_LOREM * 5)
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].step_index is None


def test_procedure_splits_on_step_sections():
    steps = [Section(f"Schritt {i}", _LOREM * 10, 3) for i in range(1, 4)]
    doc = _base_doc(doc_type="procedure", sections=steps)
    chunks = chunk_document(doc)
    assert len(chunks) == 3
    assert [c.step_index for c in chunks] == [0, 1, 2]
    assert all("Schritt" in c.heading_path for c in chunks)


def test_statute_single_article_is_one_chunk():
    doc = _base_doc(
        doc_type="statute",
        category="law",
        text="Jede Person hat Anspruch auf Leben.",
        law_name="Bundesverfassung",
        abbrev="BV",
        sr_number="101",
        article_number="10",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].article_number == "10"
    assert chunks[0].paragraph is None


def test_historical_uses_smaller_chunk_target():
    doc = _base_doc(doc_type="historical", sections=[Section("Geschichte", _LOREM * 60, 2)])
    chunks = chunk_document(doc)
    assert chunks
    # Historical chunks should be smaller on average than article chunks for
    # the same input. Compare:
    article_doc = _base_doc(sections=[Section("Geschichte", _LOREM * 60, 2)])
    article_chunks = chunk_document(article_doc)
    avg_hist = sum(c.token_count for c in chunks) / len(chunks)
    avg_art = sum(c.token_count for c in article_chunks) / len(article_chunks)
    assert avg_hist < avg_art


def test_chunk_ids_are_unique_per_doc():
    doc = _base_doc(sections=[Section("A", _LOREM * 20, 2), Section("B", _LOREM * 20, 2)])
    chunks = chunk_document(doc)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_doc_without_text_or_sections_raises():
    with pytest.raises(ValueError):
        chunk_document(_base_doc())
