"""
Dependency resolvers used by the SQL generation coordinator.

These components are intentionally lightweight scaffolds that can evolve
as the new architecture is fleshed out. For now they encapsulate the
existing logic fragments used to infer time windows and fetch schema
information.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TimeResolverResult:
    """Return object produced by TimeResolver."""

    def __init__(self, success: bool, window: Optional[Dict[str, Any]] = None, suggestions: Optional[list[str]] = None):
        self.success = success
        self.window = window or {}
        self.suggestions = suggestions or []


class SchemaResolverResult:
    """Return object produced by SchemaResolver."""

    def __init__(self, success: bool, schema: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.schema = schema or {}
        self.error = error


class TimeResolver:
    """
    Resolves time dependency for SQL generation.

    Note: initial version piggybacks existing time window computation utilities.
    """

    def __init__(self, container):
        self.container = container

    async def resolve(self, query: str, *, existing_window: Optional[Dict[str, Any]] = None) -> TimeResolverResult:
        if existing_window:
            return TimeResolverResult(success=True, window=existing_window)

        try:
            time_service = getattr(self.container, "time_service", None)
            if not time_service:
                logger.warning("TimeResolver: container missing time_service, falling back to placeholder behaviour")
                return TimeResolverResult(success=False, suggestions=["请明确时间范围（start_date/end_date）"])

            computed = await time_service.compute_window(query)
            return TimeResolverResult(success=True, window=computed)

        except Exception as exc:
            logger.error("TimeResolver: failed to compute window: %s", exc, exc_info=True)
            return TimeResolverResult(success=False, suggestions=["请手动指定统计时间范围"])


class SchemaResolver:
    """
    Resolves schema dependency for SQL generation.

    The resolver delegates to the existing ToolRegistry to avoid duplicating
    database access logic.
    """

    def __init__(self, container):
        self.container = container

    async def resolve(self, context: Dict[str, Any], *, tables_hint: Optional[list[str]] = None) -> SchemaResolverResult:
        try:
            tool_registry = getattr(self.container, "tool_registry", None)
            schema_tool = None
            if tool_registry:
                schema_tool = tool_registry.get("schema.get_columns")
            if not schema_tool:
                from ..tools.schema_tools import SchemaGetColumnsTool  # type: ignore

                schema_tool = SchemaGetColumnsTool(self.container)

            candidates = tables_hint or context.get("tables") or []
            if not candidates:
                logger.warning("SchemaResolver: tables hint missing, schema may be incomplete")

            result = await schema_tool.execute(
                {
                    "tables": candidates,
                    "data_source": context.get("data_source"),
                    "connection_config": context.get("data_source"),
                    "user_id": context.get("user_id"),
                }
            )

            if not result.get("success"):
                return SchemaResolverResult(success=False, error=result.get("error", "unknown_error"))

            schema = result.get("column_details") or result.get("columns") or {}
            return SchemaResolverResult(success=True, schema=schema)

        except Exception as exc:
            logger.error("SchemaResolver: failed to fetch schema: %s", exc, exc_info=True)
            return SchemaResolverResult(success=False, error=str(exc))
