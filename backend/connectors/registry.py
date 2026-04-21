"""
Connector registry — discovers every connector folder on import,
validates its manifest, instantiates its handler, and exposes a uniform
dispatch for the agent.

Contract for a connector folder <backend/connectors/foo/>:

    manifest.py   — defines `manifest: Manifest` at module level
    handler.py    — defines a class ending in `Connector` that subclasses
                    BaseConnector, sets `manifest = manifest`, and implements
                    one method per tool (matching `Tool.handler`)

Consumers import:

    from backend.connectors.registry import TOOL_DEFINITIONS, dispatch
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Callable

from backend.connectors.base import BaseConnector, Manifest, Tool

log = logging.getLogger(__name__)


class RegistryError(RuntimeError):
    pass


class _Registration:
    __slots__ = ("manifest", "tool", "callable")

    def __init__(self, manifest: Manifest, tool: Tool, fn: Callable[..., dict[str, Any]]):
        self.manifest = manifest
        self.tool = tool
        self.callable = fn


def _discover() -> dict[str, _Registration]:
    """Walk backend/connectors/* for folders containing manifest.py + handler.py."""
    import backend.connectors as pkg

    registrations: dict[str, _Registration] = {}

    for mod_info in pkgutil.iter_modules(pkg.__path__):
        if not mod_info.ispkg:
            continue  # skip top-level .py files (base.py, registry.py, etc.)

        folder = mod_info.name
        base = f"backend.connectors.{folder}"

        try:
            manifest_mod = importlib.import_module(f"{base}.manifest")
        except ModuleNotFoundError:
            log.warning("connector folder %s has no manifest.py — skipping", folder)
            continue

        manifest = getattr(manifest_mod, "manifest", None)
        if not isinstance(manifest, Manifest):
            raise RegistryError(
                f"{base}.manifest must define a module-level `manifest: Manifest`"
            )

        if manifest.id != folder:
            raise RegistryError(
                f"manifest.id '{manifest.id}' does not match folder name '{folder}'"
            )

        if not manifest.enabled:
            log.info("connector %s is disabled — skipping", folder)
            continue

        handler_mod = importlib.import_module(f"{base}.handler")
        handler_cls = _find_handler_class(handler_mod, folder)
        handler_instance = handler_cls()

        for tool in manifest.tools:
            if tool.name in registrations:
                existing = registrations[tool.name].manifest.id
                raise RegistryError(
                    f"duplicate tool name '{tool.name}' in '{folder}' "
                    f"(already registered by '{existing}')"
                )

            fn = getattr(handler_instance, tool.handler, None)
            if not callable(fn):
                raise RegistryError(
                    f"{handler_cls.__name__} is missing method '{tool.handler}' "
                    f"declared by tool '{tool.name}'"
                )

            registrations[tool.name] = _Registration(manifest, tool, fn)

    return registrations


def _find_handler_class(module: Any, folder: str) -> type[BaseConnector]:
    candidates = [
        obj for name, obj in vars(module).items()
        if isinstance(obj, type)
        and issubclass(obj, BaseConnector)
        and obj is not BaseConnector
        and obj.__module__ == module.__name__
    ]
    if not candidates:
        raise RegistryError(
            f"{module.__name__} must define a BaseConnector subclass for '{folder}'"
        )
    if len(candidates) > 1:
        names = ", ".join(c.__name__ for c in candidates)
        raise RegistryError(
            f"{module.__name__} defines multiple BaseConnector subclasses ({names}); "
            f"exactly one is allowed"
        )
    return candidates[0]


# --- Public surface ---------------------------------------------------------

_registry: dict[str, _Registration] = _discover()


def tool_definitions() -> list[dict[str, Any]]:
    """OpenAI/Ollama function-calling schema for every registered tool."""
    return [
        {
            "type": "function",
            "function": {
                "name": reg.tool.name,
                "description": reg.tool.description,
                "parameters": reg.tool.parameters,
            },
        }
        for reg in _registry.values()
    ]


TOOL_DEFINITIONS = tool_definitions()


def dispatch(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a tool by name. Returns the standard {success,data,source,error} envelope."""
    reg = _registry.get(name)
    if reg is None:
        return {
            "success": False,
            "data": None,
            "source": None,
            "error": f"Unknown tool: {name}",
        }
    try:
        return reg.callable(**(arguments or {}))
    except Exception as e:
        log.exception("connector %s raised", name)
        return {
            "success": False,
            "data": None,
            "source": {"name": reg.manifest.source.name, "type": reg.manifest.source.type},
            "error": str(e),
        }


def manifests() -> list[Manifest]:
    """Unique manifests (one per connector folder), useful for the UI catalog + embedder."""
    seen: dict[str, Manifest] = {}
    for reg in _registry.values():
        seen.setdefault(reg.manifest.id, reg.manifest)
    return list(seen.values())
