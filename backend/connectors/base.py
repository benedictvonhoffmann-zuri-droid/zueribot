"""
Connector framework — base classes + manifest schema.

Every connector lives in its own folder under backend/connectors/<id>/
and ships two files:

    manifest.py   — a module-level `manifest = Manifest(...)` object
    handler.py    — a class <Name>Connector(BaseConnector) whose methods
                    match the tool `handler` names in the manifest

The registry (registry.py) discovers all folders at import time, validates
each manifest, instantiates the handler, and exposes a uniform dispatch.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- Manifest schema ---------------------------------------------------------


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["official", "community", "scraped", "internal"]
    url: str
    license: str | None = None
    refresh: Literal["realtime", "hourly", "daily", "weekly", "static"]
    attribution_required: bool = False


class Runtime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    env: list[str] = Field(default_factory=list)
    timeout_s: int = 10
    rate_limit_per_min: int | None = None
    cache_ttl_s: int = 0
    failure_mode: Literal["return_error", "return_stale", "raise"] = "return_error"


class Retrieval(BaseModel):
    """Text that will be embedded by the reranker/vector store.

    Everything here should be natural language. Do not put JSON schema or
    parameter names in these fields — that's what `Tool.parameters` is for.
    """
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=20)
    example_queries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    not_for: list[str] = Field(default_factory=list)


class Tool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str                      # LLM-facing tool name (unique across the registry)
    handler: str                   # method name on the handler class
    description: str               # LLM-facing one-liner (sent in the tool schema)
    retrieval: Retrieval           # embedded by the reranker; never sent to the LLM
    parameters: dict[str, Any]     # OpenAI/Ollama function-calling JSON schema
    returns: dict[str, Any] | None = None   # doc hint for humans + reranker


Category = Literal[
    "environment",
    "mobility",
    "civic",
    "culture",
    "safety",
    "knowledge",
    "utility",
]

Pod = Literal["app", "ai"]


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                        # must match folder name
    version: int = 1
    enabled: bool = True
    category: Category
    pod: Pod = "app"

    source: Source
    runtime: Runtime = Field(default_factory=Runtime)
    tools: list[Tool] = Field(min_length=1)


# --- Base handler ------------------------------------------------------------


class BaseConnector:
    """Base class for every connector handler.

    Subclasses must set the class-level `manifest` attribute and implement one
    method per tool, matching the `handler` name declared in the manifest.
    """

    manifest: Manifest

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "manifest", None) is None:
            raise TypeError(
                f"{cls.__name__} must set a class-level `manifest = Manifest(...)`"
            )

    # --- response envelope helpers ---

    def ok(self, data: Any) -> dict[str, Any]:
        return {
            "success": True,
            "data": data,
            "source": {"name": self.manifest.source.name, "type": self.manifest.source.type},
            "error": None,
        }

    def err(self, msg: str | Exception) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "source": {"name": self.manifest.source.name, "type": self.manifest.source.type},
            "error": str(msg),
        }
