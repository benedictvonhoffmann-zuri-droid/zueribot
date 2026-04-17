"""End-to-end self-play + judgement.

Usage:
    python -m evals.run --personas all --turns 4 \
        --out evals/reports/$(date +%F).md

For a fast smoke run:
    python -m evals.run --personas ana_kreis4,priya_tourist --turns 2
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import traceback
from collections import defaultdict
from statistics import mean

import yaml

from .judge import judge_conversation
from .simulator import next_user_turn
from .subject_client import ask_subject

HERE = pathlib.Path(__file__).resolve().parent
PERSONAS_FILE = HERE / "personas.yaml"
TRANSCRIPTS_DIR = HERE / "transcripts"
REPORTS_DIR = HERE / "reports"


def load_personas() -> list[dict]:
    return yaml.safe_load(PERSONAS_FILE.read_text())["personas"]


def run_one(persona: dict, seed: str, turns: int,
            sim_model: str, judge_model: str, subject_model: str) -> dict:
    transcript: list[dict] = []
    latencies: list[float] = []
    errors: list[str] = []

    for turn_i in range(turns):
        # 1. Simulator produces user message
        try:
            user_msg = next_user_turn(sim_model, persona, seed, transcript)
        except Exception as e:
            errors.append(f"sim_turn_{turn_i}: {e}")
            break
        if not user_msg or "__DONE__" in user_msg:
            break
        transcript.append({"role": "user", "content": user_msg})

        # 2. Ask subject (Bünzli)
        try:
            reply = ask_subject(transcript, model=subject_model)
        except Exception as e:
            errors.append(f"subject_turn_{turn_i}: {e}")
            transcript.append({"role": "assistant", "content": f"[ERROR: {e}]"})
            break
        latencies.append(reply["latency_s"])
        transcript.append({"role": "assistant", "content": reply["content"]})

    # 3. Judge
    if len(transcript) >= 2:
        try:
            verdict = judge_conversation(judge_model, persona, transcript, seed)
        except Exception as e:
            verdict = {"error": f"judge_exception: {e}"}
    else:
        verdict = {"error": "empty_transcript"}

    return {
        "persona_id": persona["id"],
        "seed": seed,
        "transcript": transcript,
        "latencies_s": latencies,
        "errors": errors,
        "verdict": verdict,
    }


def avg_score(results: list[dict], axis: str) -> float | None:
    vals = []
    for r in results:
        s = r.get("verdict", {}).get("scores", {}).get(axis)
        if isinstance(s, (int, float)):
            vals.append(s)
    return round(mean(vals), 2) if vals else None


def write_report(results: list[dict], out_path: pathlib.Path,
                 started: dt.datetime, elapsed_s: float,
                 sim_model: str, judge_model: str) -> None:
    axes = ["factual", "grounding", "register", "helpfulness",
            "refusal_safety", "tone"]

    lines: list[str] = []
    lines.append(f"# Bünzli Self-Play Report — {started:%Y-%m-%d %H:%M}")
    lines.append("")
    lines.append(f"- Scenarios: **{len(results)}**")
    lines.append(f"- Wallclock: **{elapsed_s/60:.1f} min**")
    lines.append(f"- Simulator: `{sim_model}`  ·  Judge: `{judge_model}`")
    lines.append("")

    # --- Scoreboard (overall) ------------------------------------------------
    lines.append("## Scoreboard (overall, avg 1–5)")
    lines.append("")
    lines.append("| " + " | ".join(axes) + " |")
    lines.append("|" + "---|" * len(axes))
    lines.append("| " + " | ".join(
        (f"{avg_score(results, a):.2f}" if avg_score(results, a) is not None else "–")
        for a in axes
    ) + " |")
    lines.append("")

    # --- Per-persona --------------------------------------------------------
    lines.append("## Per-persona")
    lines.append("")
    lines.append("| persona | " + " | ".join(axes) + " |")
    lines.append("|---|" + "---|" * len(axes))
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_persona[r["persona_id"]].append(r)
    for pid, rows in sorted(by_persona.items()):
        cells = []
        for a in axes:
            v = avg_score(rows, a)
            cells.append(f"{v:.2f}" if v is not None else "–")
        lines.append(f"| {pid} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Pattern frequency --------------------------------------------------
    pattern_counts: dict[str, int] = defaultdict(int)
    connector_gaps: dict[str, int] = defaultdict(int)
    kb_gaps: list[str] = []
    for r in results:
        v = r.get("verdict", {})
        for p in v.get("patterns", []) or []:
            pattern_counts[p] += 1
        cg = v.get("connector_gap")
        if cg and cg != "null":
            connector_gaps[cg] += 1
        kg = v.get("kb_gap")
        if kg and kg != "null":
            kb_gaps.append(kg)

    lines.append("## Pattern frequency")
    lines.append("")
    if pattern_counts:
        for p, n in sorted(pattern_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"- **{p}**: {n}×")
    else:
        lines.append("_(no patterns flagged)_")
    lines.append("")

    lines.append("## Connector gaps (should have fired, didn't)")
    lines.append("")
    if connector_gaps:
        for c, n in sorted(connector_gaps.items(), key=lambda kv: -kv[1]):
            lines.append(f"- `{c}`: {n}×")
    else:
        lines.append("_(none flagged)_")
    lines.append("")

    lines.append("## Knowledge-base gaps (judge said: no source exists)")
    lines.append("")
    if kb_gaps:
        for k in kb_gaps[:20]:
            lines.append(f"- {k}")
    else:
        lines.append("_(none flagged)_")
    lines.append("")

    # --- Worst turns --------------------------------------------------------
    def total_score(r):
        s = r.get("verdict", {}).get("scores", {})
        if not s:
            return 999
        return sum(v for v in s.values() if isinstance(v, (int, float)))

    worst = sorted(results, key=total_score)[:10]
    lines.append("## Worst 10 conversations")
    lines.append("")
    for i, r in enumerate(worst, 1):
        v = r.get("verdict", {})
        scores = v.get("scores", {})
        score_str = " ".join(f"{a[:3]}={scores.get(a, '–')}" for a in axes)
        lines.append(f"### {i}. `{r['persona_id']}` — {score_str}")
        lines.append("")
        lines.append(f"**Seed:** {r['seed']}")
        lines.append("")
        for turn in r["transcript"]:
            role = "🧑 USER" if turn["role"] == "user" else "🤖 BÜNZLI"
            content = turn["content"].strip()
            if len(content) > 1200:
                content = content[:1200] + " …[truncated]"
            lines.append(f"**{role}:** {content}")
            lines.append("")
        if isinstance(v.get("rationale"), dict):
            lines.append("**Judge:**")
            for a in axes:
                rat = v["rationale"].get(a, "")
                lines.append(f"- _{a}_ ({scores.get(a, '–')}): {rat}")
            lines.append("")
        if v.get("error"):
            lines.append(f"_Judge error: {v['error']}_")
            lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--personas", default="all",
                    help="comma-separated persona ids, or 'all'")
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--seeds-per-persona", type=int, default=2,
                    help="how many seed questions per persona to run")
    ap.add_argument("--sim-model", default="qwen2.5:7b")
    ap.add_argument("--judge-model", default="qwen2.5:14b")
    ap.add_argument("--subject-model", default="zuribot")
    ap.add_argument("--out", default=None,
                    help="output markdown path; default reports/YYYY-MM-DD.md")
    args = ap.parse_args()

    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    personas = load_personas()
    if args.personas != "all":
        wanted = set(args.personas.split(","))
        personas = [p for p in personas if p["id"] in wanted]
    if not personas:
        print("no personas selected", file=sys.stderr)
        sys.exit(2)

    started = dt.datetime.now()
    stamp = started.strftime("%Y-%m-%d_%H%M")
    out_path = pathlib.Path(args.out) if args.out else REPORTS_DIR / f"{stamp}.md"
    raw_path = TRANSCRIPTS_DIR / f"{stamp}.jsonl"

    print(f"[eval] {len(personas)} personas × {args.seeds_per_persona} seeds × "
          f"≤{args.turns} turns → {out_path}")
    print(f"[eval] sim={args.sim_model} judge={args.judge_model} "
          f"subject={args.subject_model}")

    results: list[dict] = []
    t0 = time.time()
    with raw_path.open("w") as raw_f:
        for persona in personas:
            seeds = persona["seeds"][:args.seeds_per_persona]
            for seed in seeds:
                print(f"  · {persona['id']} :: {seed[:80]}")
                try:
                    r = run_one(persona, seed, args.turns,
                                args.sim_model, args.judge_model,
                                args.subject_model)
                except Exception as e:
                    traceback.print_exc()
                    r = {"persona_id": persona["id"], "seed": seed,
                         "transcript": [], "errors": [f"fatal: {e}"],
                         "verdict": {"error": str(e)}}
                results.append(r)
                raw_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                raw_f.flush()
                scores = r.get("verdict", {}).get("scores", {})
                if scores:
                    total = sum(v for v in scores.values() if isinstance(v, (int, float)))
                    print(f"     → total={total}/30  latency_avg="
                          f"{(sum(r['latencies_s'])/max(len(r['latencies_s']),1)):.1f}s")
                else:
                    print(f"     → judge error: {r.get('verdict', {}).get('error')}")

    elapsed = time.time() - t0
    write_report(results, out_path, started, elapsed,
                 args.sim_model, args.judge_model)
    print(f"[eval] wrote {out_path}  ({elapsed/60:.1f} min)")
    print(f"[eval] raw transcripts: {raw_path}")


if __name__ == "__main__":
    main()
