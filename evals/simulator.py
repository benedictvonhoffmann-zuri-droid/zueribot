"""User simulator — roleplays a persona and produces follow-up turns.

The simulator only ever emits the *next user message*, never commentary.
Its system prompt bakes in the persona profile, register, and seed question.
"""

from __future__ import annotations

from .ollama_client import chat

SIM_SYSTEM = """Du bist ein Roleplay-Agent. Du SPIELST eine reale Person,
die mit einem Zürcher Stadt-Chatbot namens Bünzli redet.

PERSONA:
{persona_block}

Regeln:
- Antworte IMMER nur als die Person — keine Meta-Kommentare, keine Anführungszeichen.
- Bleib in ihrem Sprachregister ({register}): wenn Züridütsch, dann wirklich
  Züridütsch (chunnt, isch, git, het, …). Wenn Englisch, dann Englisch.
- Stell natürliche Rückfragen wenn der Bot unklar war.
- Wenn der Bot eine vernünftige Antwort gegeben hat, dann hake NATÜRLICH nach
  (Details, Gegenprobe, anderer Aspekt deines Lebens) — oder sag knapp "danke"
  und beende mit dem Token __DONE__.
- Wenn der Bot halluziniert oder ausweicht, bohre nach wie eine echte Person.
- Halte dich KURZ (1–3 Sätze pro Turn), wie im echten Chat.

Die erste Nachricht ist deine Seed-Frage:
  {seed}

Ab Turn 2 produzierst du die nächste logische User-Nachricht im Gespräch.
"""


def build_sim_system(persona: dict, seed: str) -> str:
    block = (
        f"- Name: {persona['name']}\n"
        f"- Alter: {persona['age']}\n"
        f"- Quartier/Ort: {persona['quartier']}\n"
        f"- Register: {persona['register']}\n"
        f"- Kontext: {persona['context'].strip()}"
    )
    return SIM_SYSTEM.format(persona_block=block, register=persona["register"], seed=seed)


def next_user_turn(model: str, persona: dict, seed: str,
                   transcript: list[dict]) -> str:
    """Given the dialog so far (list of {role, content}), generate the next
    user message. The simulator sees the subject's replies as 'assistant'
    turns and its own as 'user' turns — but we flip them when talking to
    the sim, because *from the sim's POV* it is the user."""

    sim_messages = [{"role": "system", "content": build_sim_system(persona, seed)}]

    if not transcript:
        # First turn: the sim should just output the seed
        return seed

    # Build the dialog history from the simulator's perspective:
    #   subject's replies → "assistant" (the bot it is talking to)
    #   sim's prior user turns → "user" (itself)
    for turn in transcript:
        sim_messages.append({"role": turn["role"], "content": turn["content"]})
    sim_messages.append({
        "role": "user",
        "content": "Produziere jetzt die nächste User-Nachricht (1–3 Sätze, im Register, ohne Anführungszeichen, ohne Meta). Wenn du fertig bist, antworte nur mit: __DONE__",
    })

    reply = chat(model, sim_messages, temperature=0.9).strip()
    # strip accidental role prefixes
    for prefix in ("User:", "user:", "Frage:", "Persona:"):
        if reply.startswith(prefix):
            reply = reply[len(prefix):].strip()
    return reply
