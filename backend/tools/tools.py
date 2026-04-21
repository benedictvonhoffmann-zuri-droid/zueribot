"""Backwards-compatible shim over the connector registry.

Previously this module hand-maintained the OpenAI/Ollama tool schema list
and a 160-line if/elif dispatch over connector functions. That lookup now
lives in `backend.connectors.registry`, which discovers every connector
folder at import time and builds `TOOL_DEFINITIONS` from each manifest.

Kept as a shim so existing callers (e.g. `backend.agent`) don't need to
change import paths. New code should import from the registry directly.
"""

from backend.connectors.registry import TOOL_DEFINITIONS, dispatch as dispatch_tool

__all__ = ["TOOL_DEFINITIONS", "dispatch_tool"]
