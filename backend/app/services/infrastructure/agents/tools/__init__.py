"""
Tool adapters bridging the legacy AutoReport agent tools with the Loom
framework.

Historically the project relied on bespoke Tool classes that exposed an
`execute(payload: Dict[str, Any])` coroutine.  Loom expects tools to follow
its `BaseTool` protocol, so we provide a thin adapter layer that wraps the
existing implementations without forcing an immediate rewrite.
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from loom.interfaces.tool import BaseTool
from loom.tooling import tool as loom_tool

from ..config import ToolFactory

logger = logging.getLogger(__name__)


def adapt_legacy_tool(tool_cls: type) -> ToolFactory:
    """
    Convert a legacy Tool implementation (with an async `execute` method) into
    a Loom-compatible tool factory.
    """

    def factory(container: Any = None) -> BaseTool:
        tool_instance = None
        last_error: Optional[Exception] = None

        if container is not None:
            try:
                tool_instance = tool_cls(container)
            except TypeError as exc:
                last_error = exc
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to instantiate tool %s with container: %s", tool_cls.__name__, exc)
                last_error = exc

        if tool_instance is None:
            try:
                tool_instance = tool_cls()
            except TypeError as exc:
                if last_error:
                    raise last_error
                raise exc

        name = getattr(tool_instance, "name", tool_cls.__name__)
        description = getattr(tool_instance, "description", "") or (
            tool_cls.__doc__ or name
        )

        @loom_tool(name=name, description=description)
        async def _runner(payload: Dict[str, Any] | None = None, **kwargs) -> Dict[str, Any]:
            data: Dict[str, Any] = {}
            if payload:
                data.update(payload)
            if kwargs:
                data.update(kwargs)
            result = await tool_instance.execute(data)
            if not isinstance(result, dict):
                return {"success": True, "result": result}
            return result

        return _runner()

    return factory


def _import_tool(path: str, class_name: str) -> Optional[type]:
    try:
        module = importlib.import_module(path)
        return getattr(module, class_name)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to import tool %s.%s: %s", path, class_name, exc)
        return None


DEFAULT_TOOL_SPECS: Tuple[Tuple[str, str], ...] = (
    ("app.services.infrastructure.agents.tools.schema_tools", "SchemaListTablesTool"),
    ("app.services.infrastructure.agents.tools.schema_tools", "SchemaListColumnsTool"),
    ("app.services.infrastructure.agents.tools.schema_tools", "SchemaGetColumnsTool"),
    ("app.services.infrastructure.agents.tools.sql_tools", "SQLValidateTool"),
    ("app.services.infrastructure.agents.tools.sql_tools", "SQLExecuteTool"),
    ("app.services.infrastructure.agents.tools.sql_tools", "SQLRefineTool"),
    ("app.services.infrastructure.agents.tools.sql_tools", "SQLPolicyTool"),
    ("app.services.infrastructure.agents.tools.time_tools", "TimeWindowTool"),
)


@loom_tool(
    name="debug.echo",
    description="Echo the provided message and payload. Useful for smoke tests.",
)
async def _debug_echo(message: str = "", payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "payload": payload or {},
    }


def build_debug_tool_factory() -> ToolFactory:
    """Return a tool factory that ignores the container and produces the debug tool."""

    def factory(*_: Any, **__: Any) -> BaseTool:
        return _debug_echo()

    return factory


@lru_cache(maxsize=1)
def build_default_tool_factories() -> Tuple[ToolFactory, ...]:
    """
    Load the standard set of legacy tools and expose them as Loom tool factories.
    Tools that fail to import are skipped, allowing the runtime to operate in
    reduced capability modes during early integration.
    """

    factories: List[ToolFactory] = [build_debug_tool_factory()]
    for module_path, class_name in DEFAULT_TOOL_SPECS:
        cls = _import_tool(module_path, class_name)
        if cls is None:
            continue
        factories.append(adapt_legacy_tool(cls))
    return tuple(factories)


__all__ = [
    "adapt_legacy_tool",
    "build_default_tool_factories",
    "build_debug_tool_factory",
]
