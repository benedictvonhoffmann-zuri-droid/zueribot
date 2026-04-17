# Bünzli Eval v2 — Concept

**Scope:** pre-prod UX/usefulness gate. Not a research-grade eval.
Assumes the underlying model is already good (labs did their work).
We only measure whether **our system around it** — prompt, KB, connectors —
delivers a useful experience.

## Goals

1. Catch regressions in UX/usefulness before they hit users.
2. Quantify connector reliability programmatically, not by LLM opinion.
3. Keep wall-clock under ~20 min so it can run in a pre-merge hook.

## Non-goals

- Multi-judge / inter-rater calibration — overkill at our scale.
- Ground-truth reference answers — too expensive to maintain.
- Adversarial red-teaming — labs already stress the base model.

---

## Pieces to build (incremental on v1)

### 1. Deterministic seed set (v1 critique #4)

- Fix the seed list (~60 prompts) in `evals/seeds_v2.yaml`.
- Set simulator `temperature=0` and `seed=<fixed int>` so follow-ups are
  reproducible turn-by-turn.
- Goal: identical input → identical output (within Ollama's limits).
- **Deliverable:** re-running the eval twice back-to-back gives ≤2-point
  total drift across all scenarios.

### 2. Cross-family simulator (v1 critique #5, maybe)

- Swap simulator from `qwen2.5:7b` to `llama3` (different family, already
  local). Optional — only if we notice the Qwen sim is too nice to Qwen.
- Quick A/B: same personas, Qwen-sim vs Llama-sim, compare which finds more
  problems. Keep whichever surfaces more real issues.

### 3. Regression baseline + threshold (v1 critique #6)

- `evals/baseline.json` — pinned per-axis and per-persona averages from a
  blessed run.
- `evals/run.py` gains `--compare-baseline evals/baseline.json` that exits
  non-zero if any axis drops >0.5 or any persona total drops >3.
- One-line CI check: `python -m evals.run … --compare-baseline …`
- Bless a new baseline with `--bless` after a reviewed prompt/KB change.

### 4. Programmatic connector-trace checks (v1 critique #7)

This is the biggest lever for usefulness.

- Extend `api_server.py` to include tool-call traces in the response — either
  via a `debug=True` query param or a separate `/v1/chat/completions/trace`
  endpoint. Non-breaking for OpenWebUI.
- Each scenario in `seeds_v2.yaml` gets `expected_tools: [...]` and
  optionally `forbidden_tools: [...]`.
- Add `connector_trace.py` that parses the trace and emits binary pass/fail:
  - `expected_tools_called` (all of them fired at least once)
  - `no_forbidden_tools_called`
  - `no_hallucinated_realtime` (if response claims live data, at least one
    realtime connector must have fired)
- These run **before** the judge and are reported as hard pass/fail, not
  1–5 scores.

### 5. Binary task-specific rubrics (v1 critique #8)

Replace the 6-axis Likert with a hybrid:

**Hard checks (binary, computed, not judge):**
- `language_match` — detect user language, check reply language.
  ([langdetect] or first-N-chars heuristic; Züridütsch marker words.)
- `has_citations` — regex for `[Quelle:` / markdown links / connector names.
- `under_length_cap` — no response over 2000 chars unless user asked for
  detail.
- `expected_tools_called` — from §4.

**Judge checks (still 1–5, but only where binary can't work):**
- `helpfulness` — did it answer the actual question?
- `tone` — Zürcher dry-but-useful vs. marketing fluff.

The hard checks are what the CI gate actually blocks on; judge scores are
directional signal for humans reading the report.

---

## Report v2 format

Top of the report:

```
HARD CHECKS       pass/total   regression?
language_match    58/60        ok
has_citations     52/60        ⚠ -3 vs baseline
expected_tools    49/60        ⚠ -5 vs baseline
no_hallucinated   57/60        ok

SOFT SCORES (1-5) avg  Δ-vs-baseline
helpfulness       4.1  -0.2
tone              3.9  +0.1
```

Below that: the worst 10 conversations (same as v1) — unchanged because
it's the most useful artifact for humans.

---

## Build order (suggestive)

1. Expose tool-call traces in FastAPI (§4 endpoint bit) — enables
   everything else and is ~30 lines.
2. Add `expected_tools` to seeds and the `connector_trace.py` checker.
3. Add the binary language/citation checks. Drop the 4 Likert axes those
   replace.
4. Freeze a baseline, add `--compare-baseline`.
5. Wire into `make preflight` / pre-push hook.
6. (Optional) cross-family sim A/B.

Each step is independently useful; can stop after #2 and already be ahead
of v1.

## Out of scope for v2

- Replaying real user traffic (needs production logs + privacy review).
- Multi-turn conversation depth >3 (diminishing returns vs wall-clock cost).
- Anything requiring a human labeller in the loop.
