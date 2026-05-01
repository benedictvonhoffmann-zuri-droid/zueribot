"""Structural chunker — spec §5 and §6.

Public API: ``chunk_document(doc)`` returning ``list[Chunk]``.

Strategy (spec §5.1):
    1. Structural split on H1/H2/H3 + paragraph boundaries.
    2. Recursive character fallback if structure is weak.
    3. Fixed token windows as last resort.

Size targets (§5.2): 400-600 tokens, overlap 10-15%, hard max 1000,
hard min 100. Never split mid-sentence.

Per-doc_type dispatch (§5.3):
    article     -> structural + 400-600 tokens
    procedure   -> whole if <=800 tokens else split on steps
    reference   -> one chunk, no splitting
    statute     -> one article = one chunk, split on Absatz if >2000
    historical  -> structural + 300-400 tokens
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from backend.kb.metadata import (
    Authority,
    Category,
    Chunk,
    DocType,
    make_chunk_id,
    make_doc_id,
)
from backend.kb.tokenizer import count_tokens

logger = logging.getLogger("zuribot.kb.chunker")

TARGET_MIN = 400
TARGET_MAX = 600
HARD_MIN = 100
HARD_MAX = 1000
OVERLAP_RATIO = 0.125  # ~12.5%, centre of the 10-15% band
PARENT_THRESHOLD = 1200  # spec §6
PROCEDURE_WHOLE_LIMIT = 800
STATUTE_ABSATZ_SPLIT = 2000

# Historical blends better as smaller chunks (spec §5.3)
HISTORICAL_MIN = 300
HISTORICAL_MAX = 400

# Safety guard: a single section longer than this (in characters) is almost
# always page noise (boilerplate dumps, JS payload bleed-through, navigation
# turned into prose). Tokenizing huge inputs is slow and they yield low-value
# chunks. Truncate with a warning.
MAX_SECTION_CHARS = 80_000


@dataclass
class Section:
    """Structural unit emitted by the splitter — one heading + its body."""

    heading: str
    text: str
    level: int  # 1..3


@dataclass
class Document:
    """Input to ``chunk_document``."""

    source_url: str
    source_name: str
    title: str
    language: str
    category: Category
    authority: Authority
    doc_type: DocType
    # Either ``sections`` (structural input) or ``text`` (flat) must be set.
    sections: list[Section] = field(default_factory=list)
    text: str = ""
    subcategory: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    ttl_days: Optional[int] = None
    district: Optional[str] = None
    license: Optional[str] = None
    # doc_type-specific context
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None
    law_name: Optional[str] = None
    abbrev: Optional[str] = None
    sr_number: Optional[str] = None
    ls_number: Optional[str] = None
    article_number: Optional[str] = None
    period: Optional[str] = None


# ── Sentence-safe text splitting ───────────────────────────────────────────

_SENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")
_PARAGRAPH = re.compile(r"\n\s*\n")


def _sentences(text: str) -> list[str]:
    """Split to sentences. Good enough for DE + EN prose."""
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_BOUNDARY.split(text) if s.strip()]


def _pack_sentences(
    sentences: list[str],
    target_max: int,
    overlap_ratio: float,
) -> list[str]:
    """Pack sentences into chunks in the target token range with overlap.

    Greedy: grow a chunk until adding the next sentence would exceed
    target_max, then emit. Overlap = last N sentences re-used as the
    start of the next chunk, sized by token ratio.
    """
    if not sentences:
        return []

    chunks: list[str] = []
    cur: list[str] = []
    cur_tokens = 0

    i = 0
    while i < len(sentences):
        s = sentences[i]
        s_tokens = count_tokens(s)

        # Guard: a single sentence bigger than target_max gets emitted alone.
        # (Below target_max means it can combine with neighbours; above means
        # combining would either overflow target_max or — worse — leave us
        # in an infinite emit-and-seed loop because the seeded overlap can
        # never make room for a sentence that's already past target_max.)
        if s_tokens > target_max:
            if cur:
                chunks.append(" ".join(cur))
                cur, cur_tokens = [], 0
            chunks.append(s)
            i += 1
            continue

        would_be = cur_tokens + s_tokens
        if cur and would_be > target_max:
            chunks.append(" ".join(cur))
            # Seed next chunk with the tail of this one for overlap.
            overlap_budget = int(target_max * overlap_ratio)
            tail: list[str] = []
            tail_tokens = 0
            for prev in reversed(cur):
                t = count_tokens(prev)
                if tail_tokens + t > overlap_budget:
                    break
                tail.insert(0, prev)
                tail_tokens += t
            # Progress guard: if the seeded tail still leaves no room for s,
            # drop the tail. s will start the next chunk alone (since
            # s_tokens <= target_max here, that's safe).
            if tail_tokens + s_tokens > target_max:
                tail, tail_tokens = [], 0
            cur = tail
            cur_tokens = tail_tokens
            continue

        cur.append(s)
        cur_tokens += s_tokens
        i += 1

    if cur and cur_tokens >= HARD_MIN:
        chunks.append(" ".join(cur))
    elif cur and chunks:
        # Tail too small — fold into previous.
        chunks[-1] = chunks[-1] + " " + " ".join(cur)
    elif cur:
        # Doc is just a single tiny bit; keep it anyway.
        chunks.append(" ".join(cur))

    return chunks


# ── Heading path builders ──────────────────────────────────────────────────

def _heading_path(doc: Document, *extra: str) -> str:
    parts = [doc.source_name, doc.title, *[e for e in extra if e]]
    return " > ".join(parts)


# ── Per-doc_type chunkers ──────────────────────────────────────────────────

def _chunk_article(doc: Document, target_max: int) -> list[tuple[str, str, Optional[str]]]:
    """Return (display_text, heading_path_suffix, parent_ref_key) triples.

    parent_ref_key is a key identifying which parent section the child
    belongs to; it maps to an entry in the later parent-pass.
    """
    results: list[tuple[str, str, Optional[str]]] = []

    sections = doc.sections or [Section(heading="", text=doc.text, level=2)]

    for sec in sections:
        section_tokens = count_tokens(sec.text)
        parent_key: Optional[str] = None
        if section_tokens > PARENT_THRESHOLD:
            parent_key = sec.heading or "body"

        sentences = _sentences(sec.text)
        pieces = _pack_sentences(sentences, target_max, OVERLAP_RATIO)
        for piece in pieces:
            results.append((piece, sec.heading, parent_key))

    return results


def _chunk_procedure(doc: Document) -> list[tuple[str, str, Optional[int]]]:
    """Whole if small; else one chunk per step, never splitting a step."""
    whole = doc.text or "\n\n".join(s.text for s in doc.sections)
    total = count_tokens(whole)
    if total <= PROCEDURE_WHOLE_LIMIT and not doc.sections:
        return [(whole.strip(), "", None)]

    if doc.sections:
        out: list[tuple[str, str, Optional[int]]] = []
        for i, sec in enumerate(doc.sections):
            out.append((sec.text.strip(), sec.heading, i))
        return out

    # Flat procedure text above the whole-limit: fall back to article packing.
    pieces = _pack_sentences(
        _sentences(whole), TARGET_MAX, OVERLAP_RATIO,
    )
    return [(p, "", i) for i, p in enumerate(pieces)]


def _chunk_reference(doc: Document) -> list[tuple[str, str]]:
    """One entity = one chunk. Never split."""
    text = doc.text or "\n".join(s.text for s in doc.sections)
    return [(text.strip(), "")]


def _chunk_statute(doc: Document) -> list[tuple[str, str, Optional[str]]]:
    """One article = one chunk; split on Absatz boundaries if >2000 tokens."""
    text = (doc.text or "\n".join(s.text for s in doc.sections)).strip()
    tokens = count_tokens(text)
    if tokens <= STATUTE_ABSATZ_SPLIT:
        return [(text, "", None)]

    # Split on Absatz markers like "1 " / "2 " or "Abs. 1".
    absatz_split = re.split(r"(?=^\s*\d+\s)", text, flags=re.MULTILINE)
    out = [(part.strip(), "", str(i + 1)) for i, part in enumerate(absatz_split) if part.strip()]
    return out or [(text, "", None)]


def _chunk_historical(doc: Document) -> list[tuple[str, str, Optional[str]]]:
    """Same as article but with smaller target range."""
    return _chunk_article(doc, HISTORICAL_MAX)


# ── Public entry point ────────────────────────────────────────────────────

def chunk_document(doc: Document) -> list[Chunk]:
    """Chunk a document according to its doc_type. Returns Chunk objects.

    The caller is responsible for constructing the Document with the
    appropriate sections (from HTML parsing) or flat text.
    """
    if not doc.sections and not doc.text:
        raise ValueError("Document must have either sections or text")
    if doc.created_at is None or doc.updated_at is None:
        raise ValueError("created_at and updated_at are required")

    for sec in doc.sections:
        if len(sec.text) > MAX_SECTION_CHARS:
            logger.warning(
                "truncating oversized section url=%s heading=%r %d->%d chars",
                doc.source_url, sec.heading, len(sec.text), MAX_SECTION_CHARS,
            )
            sec.text = sec.text[:MAX_SECTION_CHARS]
    if len(doc.text) > MAX_SECTION_CHARS:
        logger.warning(
            "truncating oversized doc.text url=%s %d->%d chars",
            doc.source_url, len(doc.text), MAX_SECTION_CHARS,
        )
        doc.text = doc.text[:MAX_SECTION_CHARS]

    doc_id = make_doc_id(doc.source_url, doc.language)

    dispatch = {
        "article": lambda: _chunk_article(doc, TARGET_MAX),
        "historical": lambda: _chunk_historical(doc),
        "procedure": lambda: _chunk_procedure(doc),
        "reference": lambda: _chunk_reference(doc),
        "statute": lambda: _chunk_statute(doc),
    }
    raw = dispatch[doc.doc_type]()

    # Collect parent sections first (article / historical only).
    parent_map: dict[str, str] = {}
    if doc.doc_type in ("article", "historical"):
        for sec in doc.sections:
            if count_tokens(sec.text) > PARENT_THRESHOLD:
                parent_map[sec.heading or "body"] = sec.text.strip()

    chunks: list[Chunk] = []
    parent_chunk_ids: dict[str, str] = {}

    # Emit parent chunks first so children can reference them.
    for i, (key, text) in enumerate(parent_map.items(), start=1):
        pidx = f"P{i:02d}"
        pid = make_chunk_id(doc_id, pidx)
        parent_chunk_ids[key] = pid
        heading = key if key != "body" else ""
        hp = _heading_path(doc, heading) if heading else _heading_path(doc)
        chunks.append(_build(doc, doc_id, pidx, None, text, heading, hp))

    # Emit children.
    for idx, entry in enumerate(raw):
        if doc.doc_type in ("article", "historical"):
            piece, heading, parent_key = entry
            parent_id = parent_chunk_ids.get(parent_key) if parent_key else None
            step_index = None
            paragraph = None
        elif doc.doc_type == "procedure":
            piece, heading, step_index = entry
            parent_id = None
            paragraph = None
        elif doc.doc_type == "statute":
            piece, heading, paragraph = entry
            parent_id = None
            step_index = None
        else:  # reference
            piece, heading = entry
            parent_id = None
            step_index = None
            paragraph = None

        hp = _heading_path(doc, heading) if heading else _heading_path(doc)
        chunks.append(_build(
            doc, doc_id, idx, parent_id, piece, heading, hp,
            step_index=step_index, paragraph=paragraph,
        ))

    return chunks


def _build(
    doc: Document,
    doc_id: str,
    chunk_index: int | str,
    parent_chunk_id: Optional[str],
    display_text: str,
    _section_heading: str,
    heading_path: str,
    *,
    step_index: Optional[int] = None,
    paragraph: Optional[str] = None,
) -> Chunk:
    embed_text = f"{heading_path}\n\n{display_text}"
    return Chunk(
        chunk_id=make_chunk_id(doc_id, chunk_index),
        doc_id=doc_id,
        chunk_index=chunk_index,
        parent_chunk_id=parent_chunk_id,
        source_url=doc.source_url,
        source_name=doc.source_name,
        title=doc.title,
        heading_path=heading_path,
        language=doc.language,
        category=doc.category,
        subcategory=doc.subcategory,
        authority=doc.authority,
        doc_type=doc.doc_type,
        chunk_shape="prose",
        token_count=count_tokens(display_text),
        tags=doc.tags,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        ttl_days=doc.ttl_days,
        display_text=display_text,
        embed_text=embed_text,
        step_index=step_index,
        entity_name=doc.entity_name,
        entity_type=doc.entity_type,
        address=doc.address,
        law_name=doc.law_name,
        abbrev=doc.abbrev,
        sr_number=doc.sr_number,
        ls_number=doc.ls_number,
        article_number=doc.article_number,
        paragraph=paragraph,
        period=doc.period,
        district=doc.district,
        license=doc.license,
    )
