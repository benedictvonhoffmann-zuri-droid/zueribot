"""Thin Ollama HTTP client — no streaming, just blocking chat completions."""

from __future__ import annotations

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"


def chat(model: str, messages: list[dict], *, temperature: float = 0.7,
         num_ctx: int = 8192, timeout: float = 300.0) -> str:
    """Call Ollama /api/chat, return assistant content string."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(OLLAMA_URL, json=payload)
        r.raise_for_status()
        data = r.json()
    return data["message"]["content"]
