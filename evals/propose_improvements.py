"""Read a run's report + transcripts, ask the judge model to propose
concrete, actionable changes: system-prompt diffs, new KB chunks,
connector priority/trigger changes, new personas/scenarios.

Usage:
    python -m evals.propose_improvements \
        --report evals/reports/2026-04-17_2130.md \
        --transcripts evals/transcripts/2026-04-17_2130.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from .ollama_client import chat

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
PROPOSALS_DIR = HERE / "proposals"

PROPOSER_SYSTEM = """Du bist ein Senior-Prompt-Engineer und Reviewer für den
Zürcher Stadt-Chatbot Bünzli. Du liest (1) einen Eval-Report mit Scoreboard
und schlechten Transkripten, (2) einen Auszug des aktuellen SYSTEM_PROMPTs
von Bünzli, (3) die Liste der verfügbaren Connector-Tools.

Dein Output ist eine Markdown-Datei mit GENAU diesen Abschnitten in dieser
Reihenfolge:

## TL;DR — Top-5 umsetzbare Findings
5 nummerierte Bullets. Jeder ≤ 2 Zeilen. Beziffere die Evidenz (z.B.
"3/6 Züridütsch-Turns in Hochdeutsch beantwortet → register avg 2.8").

## System-Prompt-Diffs
Für jeden vorgeschlagenen Edit:
- Begründung (1 Satz)
- ```diff-Block mit -alt / +neu Zeilen (nimm die alten Zeilen WÖRTLICH aus
  dem mitgelieferten Auszug, sonst ist der Diff nicht anwendbar)
Wenn du keinen braucht, schreib „Keine Prompt-Änderungen nötig."

## Neue KB-Einträge
Für jedes Thema, das laut Judge gefehlt hat:
- **Titel**
- Quelle (URL, die ein Mensch noch verifizieren muss)
- 1-Absatz-Seed-Text (nicht halluzinieren — markiere unklare Fakten mit `??`)

## Connector-Änderungen
Für jeden Connector-Gap:
- Connector-Name
- Trigger-Regel, die fehlt (1 Satz, in Bünzli-Prompt-Stil)
- Priorität relativ zu anderen Tools

## Neue Personas / Szenarien
Kurze Liste (Name, Register, 1-Zeilen-Szenario), die blinde Flecken abdecken
(z.B. Italienisch-sprechend, Rollstuhl-Barrierefreiheit, Gewerbemieter).

WICHTIGE REGELN:
- Nur Markdown, keine Code-Fences um das ganze Dokument.
- Keine ausschweifende Theorie. Jeder Vorschlag muss direkt auf ein Beispiel
  aus dem Report verweisen.
- Wenn etwas eine manuelle Prüfung erfordert (URLs, Fakten), sag das explizit.
"""


def extract_system_prompt_excerpt(agent_path: pathlib.Path, max_chars=4000) -> str:
    """Grab the SYSTEM_PROMPT block from backend/agent.py."""
    text = agent_path.read_text()
    m = re.search(r'SYSTEM_PROMPT\s*=\s*"""(.*?)"""', text, re.DOTALL)
    if not m:
        return "(konnte SYSTEM_PROMPT nicht extrahieren)"
    body = m.group(1).strip()
    return body[:max_chars] + ("\n…[gekürzt]" if len(body) > max_chars else "")


def extract_tool_names(tools_path: pathlib.Path) -> list[str]:
    text = tools_path.read_text()
    return sorted(set(re.findall(r'"name":\s*"([a-z_]+)"', text)))


def summarise_transcripts(jsonl_path: pathlib.Path, max_bad=12) -> str:
    """Render the worst-scoring transcripts as context for the proposer."""
    rows = []
    with jsonl_path.open() as f:
        for line in f:
            rows.append(json.loads(line))

    def total(r):
        s = r.get("verdict", {}).get("scores", {})
        return sum(v for v in s.values() if isinstance(v, (int, float))) or 0

    rows.sort(key=total)
    worst = rows[:max_bad]

    blocks = []
    for r in worst:
        v = r.get("verdict", {})
        header = (
            f"### {r['persona_id']} — scores={v.get('scores')} "
            f"patterns={v.get('patterns')} "
            f"connector_gap={v.get('connector_gap')} "
            f"kb_gap={v.get('kb_gap')}"
        )
        blocks.append(header)
        blocks.append(f"seed: {r['seed']}")
        for turn in r["transcript"][:8]:
            c = turn["content"].strip()
            if len(c) > 700:
                c = c[:700] + " …"
            blocks.append(f"[{turn['role']}] {c}")
        if isinstance(v.get("rationale"), dict):
            blocks.append("judge rationale: " + json.dumps(v["rationale"], ensure_ascii=False))
        blocks.append("")
    return "\n".join(blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--model", default="qwen2.5:14b")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    report_md = pathlib.Path(args.report).read_text()
    transcripts = summarise_transcripts(pathlib.Path(args.transcripts))
    prompt_excerpt = extract_system_prompt_excerpt(REPO / "backend" / "agent.py")
    tool_names = extract_tool_names(REPO / "backend" / "tools" / "tools.py")

    user_msg = (
        "## Eval-Report\n\n" + report_md[:6000]
        + "\n\n## Schlechteste Transkripte (Roh)\n\n" + transcripts[:6000]
        + "\n\n## Aktueller SYSTEM_PROMPT-Auszug\n\n```\n" + prompt_excerpt[:3000] + "\n```\n\n"
        + "## Verfügbare Connector-Tools\n\n" + ", ".join(tool_names)
        + "\n\nSchreib jetzt die Vorschlagsdatei gemäss Schema."
    )

    print(f"[propose] model={args.model} report={args.report}  "
          f"input_chars={len(user_msg)}")
    out = chat(args.model,
               [{"role": "system", "content": PROPOSER_SYSTEM},
                {"role": "user", "content": user_msg}],
               temperature=0.2, num_ctx=16384, timeout=1800)

    PROPOSALS_DIR.mkdir(exist_ok=True)
    stamp = pathlib.Path(args.report).stem
    out_path = pathlib.Path(args.out) if args.out else PROPOSALS_DIR / f"{stamp}.md"
    out_path.write_text(out)
    print(f"[propose] wrote {out_path}")


if __name__ == "__main__":
    main()
