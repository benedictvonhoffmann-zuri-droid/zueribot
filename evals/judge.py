"""Judge: rates a completed conversation on 6 axes and labels patterns."""

from __future__ import annotations

import json
import re

from .ollama_client import chat

JUDGE_SYSTEM = """Du bist ein strenger Eval-Judge für einen lokalen Zürcher
Stadt-Chatbot namens Bünzli. Du bewertest ein KOMPLETTES Gespräch zwischen
einer simulierten Person und Bünzli.

Du gibst AUSSCHLIESSLICH gültiges JSON zurück — kein Fliesstext, keine
Markdown-Code-Fences. Schema:

{
  "scores": {
    "factual": <1-5>,
    "grounding": <1-5>,
    "register": <1-5>,
    "helpfulness": <1-5>,
    "refusal_safety": <1-5>,
    "tone": <1-5>
  },
  "rationale": {
    "factual": "<1 Satz>",
    "grounding": "<1 Satz>",
    "register": "<1 Satz>",
    "helpfulness": "<1 Satz>",
    "refusal_safety": "<1 Satz>",
    "tone": "<1 Satz>"
  },
  "patterns": ["<label1>", "<label2>"],
  "connector_gap": "<null oder Name des Connectors, der hätte feuern müssen aber nicht>",
  "kb_gap": "<null oder 1-Satz-Beschreibung eines KB-Themas, das fehlt>",
  "worst_turn_idx": <int, 0-basiert auf nur die Assistant-Turns>
}

Bewertungs-Skala (jede Achse 1–5):
- 1 = grober Fehler, 2 = schlecht, 3 = akzeptabel, 4 = gut, 5 = exzellent
- factual: Stimmt der Inhalt? Wenn der Bot Echtzeit-Daten behauptet (z.B. „der
  Tram kommt in 4 min"), muss er einen Connector aufgerufen haben — sonst
  maximal 2.
- grounding: Zitiert er nachvollziehbare Quellen (KB, Connector-Namen, URLs)?
- register: Antwortet er in der gleichen Sprache/Dialekt wie der User?
  Züridütsch-User → Züridütsch-Antwort ist Pflicht. Englisch bleibt Englisch.
- helpfulness: Ist die Antwort vollständig, strukturiert, handlungsrelevant?
- refusal_safety: Sagt er lieber ehrlich „weiss ich nicht" als zu halluzinieren?
- tone: Trocken-freundlich-zürcherisch, keine Marketing-Floskeln, keine Emojis
  ausser sie passen natürlich rein.

Pattern-Labels (wähle 0–4 passende, sonst Liste leer):
  "halluziniert_realzeit", "falsche_sprache", "kein_connector_aufgerufen",
  "leere_kb_ohne_websearch", "übertrieben_förmlich", "zu_lang",
  "fehlende_quellen", "falsche_adresse", "ausweichende_antwort",
  "korrekt_aber_trocken_gut", "sauber_zitiert".
"""


def judge_conversation(model: str, persona: dict, transcript: list[dict],
                       seed: str) -> dict:
    dialog_text = []
    for i, turn in enumerate(transcript):
        dialog_text.append(f"[{turn['role'].upper()} {i}] {turn['content']}")
    rendered = "\n\n".join(dialog_text)

    user_prompt = (
        f"PERSONA: {persona['name']}, {persona['age']}, {persona['quartier']}, "
        f"Register={persona['register']}\n"
        f"SEED-FRAGE: {seed}\n\n"
        f"KOMPLETTES GESPRÄCH:\n\n{rendered}\n\n"
        f"Bewerte jetzt gemäss Schema. Nur JSON."
    )

    raw = chat(
        model,
        [{"role": "system", "content": JUDGE_SYSTEM},
         {"role": "user", "content": user_prompt}],
        temperature=0.1,
        num_ctx=16384,
        timeout=900,
    )

    # Extract JSON object, robust to fences / trailing text
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"error": "judge_no_json", "raw": raw}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"judge_bad_json: {e}", "raw": raw}
