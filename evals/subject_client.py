"""Client that talks to the live Bünzli (zuribot) via the nginx-proxied
OpenAI-compatible endpoint.
"""

from __future__ import annotations

import time
import httpx

# zuribot lives behind nginx at /zuribot/*
SUBJECT_URL = "http://localhost/zuribot/v1/chat/completions"


def ask_subject(history: list[dict], *, model: str = "zuribot",
                timeout: float = 240.0) -> dict:
    """Send chat history to Bünzli, return {content, latency_s, raw}."""
    payload = {"model": model, "messages": history, "stream": False}
    t0 = time.time()
    with httpx.Client(timeout=timeout) as client:
        r = client.post(SUBJECT_URL, json=payload)
        r.raise_for_status()
        data = r.json()
    latency = time.time() - t0
    content = data["choices"][0]["message"]["content"]
    return {"content": content, "latency_s": round(latency, 2), "raw": data}
