"""
LLM provider configuration.
Controlled via environment variables so swapping providers requires no code changes.

Supported providers:
  anthropic  — Claude API (default, recommended)
  openai     — Any OpenAI-compatible API (includes Apertus)
  ollama     — Local Ollama (for offline dev)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env by walking up from this file's location
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # only needed for openai-compatible providers
LLM_API_KEY = os.getenv("LLM_API_KEY", "")    # only needed for openai-compatible providers


def get_llm():
    """Return a LangChain chat model based on environment config."""
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=LLM_MODEL,
            temperature=0.1,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    elif LLM_PROVIDER == "openai":
        # Works for any OpenAI-compatible API — including Apertus.
        # Set LLM_BASE_URL and LLM_API_KEY in .env to point at the provider.
        from langchain_openai import ChatOpenAI
        kwargs = dict(model=LLM_MODEL, temperature=0.1, api_key=LLM_API_KEY)
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        return ChatOpenAI(**kwargs)

    elif LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=LLM_MODEL, temperature=0.1)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use 'anthropic', 'openai', or 'ollama'.")
