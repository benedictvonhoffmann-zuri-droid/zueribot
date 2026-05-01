#!/usr/bin/env python3
"""§14 acceptance audit for the Phase 1 KB chunks.

Runs the mechanical checks from docs/knowledge_base.md §14 against every
chunk on disk, plus prints a small random sample for the human-eye checks
(self-containedness, table/list intactness).

Skips:
  - §14.5 (updated_at on re-ingest) — covered by stable doc_id hashing.
  - §14.7 (10-question retrieval test) — Phase 2 territory.
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "chunks"

URL_RE = re.compile(r"^https?://")
SENT_END = set(".!?»\"'")


_MID_WORD_START = re.compile(r"^[a-zäöüß]{2,}[a-zäöüß]")


def starts_mid_word(text: str) -> bool:
    """Chunk starts with a lowercase fragment — strong sign the splitter
    cut a word in half. Capitals at start are normal sentence beginnings."""
    s = text.lstrip()
    if not s:
        return False
    return bool(_MID_WORD_START.match(s[:30]))


def audit():
    files = list(ROOT.rglob("*.jsonl"))
    by_source: dict[tuple[str, str], list[dict]] = defaultdict(list)

    fails = defaultdict(lambda: defaultdict(int))   # source -> check -> count
    totals = defaultdict(int)
    examples = defaultdict(list)                     # check -> [(source, chunk_id, snippet)]
    grand = 0
    statute_chunks = 0
    procedure_chunks = 0
    tok_buckets = {"<100": 0, "100-399": 0, "400-600": 0, "601-1000": 0, ">1000": 0}
    oversize_examples: list[tuple] = []

    for fp in files:
        # category/source/doc_id.jsonl
        parts = fp.relative_to(ROOT).parts
        if len(parts) < 3:
            continue
        category, source = parts[0], parts[1]
        key = (category, source)

        with fp.open() as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                grand += 1
                totals[key] += 1
                if c.get("doc_type") == "statute":
                    statute_chunks += 1
                if c.get("doc_type") == "procedure":
                    procedure_chunks += 1
                by_source[key].append(c)

                # Token-count distribution
                tk = c.get("token_count") or 0
                if tk < 100:
                    tok_buckets["<100"] += 1
                elif tk < 400:
                    tok_buckets["100-399"] += 1
                elif tk <= 600:
                    tok_buckets["400-600"] += 1
                elif tk <= 1000:
                    tok_buckets["601-1000"] += 1
                else:
                    tok_buckets[">1000"] += 1
                    if len(oversize_examples) < 10:
                        oversize_examples.append((category, source, c.get("chunk_id"), tk, c.get("doc_type")))

                # 3. heading_path non-empty
                hp = c.get("heading_path") or ""
                if not hp.strip():
                    fails[key]["3_heading_path_empty"] += 1
                    if len(examples["3_heading_path_empty"]) < 5:
                        examples["3_heading_path_empty"].append((category, source, c.get("chunk_id")))

                # 4. valid source_url
                url = c.get("source_url") or ""
                if not URL_RE.match(url):
                    fails[key]["4_bad_source_url"] += 1
                    if len(examples["4_bad_source_url"]) < 5:
                        examples["4_bad_source_url"].append((category, source, c.get("chunk_id"), url))

                # 8. no mid-sentence split — flag chunks that START mid-word
                # (strong signal the chunker cut a word). Skip child chunks of
                # statutes (markers handle continuity) and chunk_index 0.
                disp = c.get("display_text") or ""
                ci_raw = c.get("chunk_index") or 0
                try:
                    ci = int(ci_raw)
                except (TypeError, ValueError):
                    ci = 0
                if (
                    ci > 0
                    and c.get("doc_type") != "statute"
                    and disp
                    and starts_mid_word(disp)
                ):
                    fails[key]["8_starts_mid_word"] += 1
                    if len(examples["8_starts_mid_word"]) < 10:
                        examples["8_starts_mid_word"].append(
                            (category, source, c.get("chunk_id"), disp[:80])
                        )

                # 9. display_text doesn't start with heading_path
                if hp and disp.lstrip().startswith(hp):
                    fails[key]["9_display_has_heading_pollution"] += 1
                    if len(examples["9_display_has_heading_pollution"]) < 5:
                        examples["9_display_has_heading_pollution"].append((category, source, c.get("chunk_id")))

                # 10. embed_text starts with heading_path (when hp is present)
                emb = c.get("embed_text") or ""
                if hp and not emb.lstrip().startswith(hp):
                    fails[key]["10_embed_missing_heading"] += 1
                    if len(examples["10_embed_missing_heading"]) < 5:
                        examples["10_embed_missing_heading"].append((category, source, c.get("chunk_id")))

    # Summary
    print(f"=== §14 audit — {grand:,} chunks across {len(by_source)} sources ===\n")
    print(f"  statute chunks:   {statute_chunks:,}")
    print(f"  procedure chunks: {procedure_chunks:,}\n")

    print("Per-check fail tallies (mechanical):")
    by_check = defaultdict(int)
    for key, check_counts in fails.items():
        for check, n in check_counts.items():
            by_check[check] += n
    for check in sorted(by_check):
        n = by_check[check]
        pct = 100 * n / grand if grand else 0
        print(f"  {check:40s} {n:7,d}  ({pct:5.2f}%)")

    print("\nTop offenders by source:")
    rows = []
    for key, check_counts in fails.items():
        total_fail = sum(check_counts.values())
        if total_fail:
            rows.append((total_fail, key, check_counts))
    rows.sort(reverse=True)
    for total_fail, (cat, src), check_counts in rows[:15]:
        n_total = totals[(cat, src)]
        print(f"  {cat}/{src}  fails={total_fail}  total={n_total}  {dict(check_counts)}")

    print("\nToken-count distribution:")
    for b, n in tok_buckets.items():
        pct = 100 * n / grand if grand else 0
        print(f"  {b:>10s}  {n:7,d}  ({pct:5.2f}%)")
    if oversize_examples:
        print("\nOversize (>1000 tokens) examples:")
        for e in oversize_examples:
            print(f"  {e}")

    print("\nExamples of each fail type:")
    for check, ex in sorted(examples.items()):
        print(f"\n[{check}]")
        for e in ex:
            print(f"  {e}")

    # Random sample for human eyes (checks 1 & 2)
    print("\n=== Random sample for §14.1 (self-contained) and §14.2 (lists/tables) ===")
    random.seed(42)
    keys = list(by_source.keys())
    random.shuffle(keys)
    seen_cats = set()
    sampled = 0
    for key in keys:
        cat, src = key
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        chunks = by_source[key]
        if not chunks:
            continue
        c = random.choice(chunks)
        print(f"\n--- {cat}/{src} :: {c.get('chunk_id')} (token_count={c.get('token_count')}) ---")
        print(f"heading_path: {c.get('heading_path')}")
        print(f"source_url:   {c.get('source_url')}")
        disp = (c.get("display_text") or "")[:600]
        print(f"display_text [first 600 chars]:\n{disp}")
        sampled += 1
        if sampled >= 11:
            break


if __name__ == "__main__":
    sys.exit(audit() or 0)
