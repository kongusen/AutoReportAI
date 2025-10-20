"""
Composable context objects used by the SQL generation coordinator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SQLReadiness(Enum):
    """Represents the readiness of the SQL context for generation."""

    READY = "ready"
    MISSING_TIME = "missing_time"
    MISSING_SCHEMA = "missing_schema"
    BLOCKED = "blocked"


@dataclass
class SQLDependencyState:
    """Tracks dependency resolution state and related metadata."""

    time_window: Optional[Dict[str, Any]] = None
    schema: Optional[Dict[str, Any]] = None
    resolved_dependencies: List[str] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)

    def mark_resolved(self, dependency: str) -> None:
        if dependency not in self.resolved_dependencies:
            self.resolved_dependencies.append(dependency)
        if dependency in self.missing_dependencies:
            self.missing_dependencies.remove(dependency)

    def mark_missing(self, dependency: str) -> None:
        if dependency not in self.missing_dependencies:
            self.missing_dependencies.append(dependency)


@dataclass
class SQLContext:
    """Aggregated context required to generate and validate SQL."""

    query: str
    dependency_state: SQLDependencyState = field(default_factory=SQLDependencyState)
    previous_attempts: List[Dict[str, Any]] = field(default_factory=list)
    user_clarifications: Dict[str, Any] = field(default_factory=dict)
    candidate_sql_history: List[str] = field(default_factory=list)

    def is_ready(self) -> SQLReadiness:
        """Returns the readiness state based on current dependencies."""
        deps = self.dependency_state
        if deps.time_window is None:
            deps.mark_missing("time_window")
            return SQLReadiness.MISSING_TIME
        if deps.schema is None:
            deps.mark_missing("schema")
            return SQLReadiness.MISSING_SCHEMA
        return SQLReadiness.READY

    @property
    def time_window(self) -> Optional[Dict[str, Any]]:
        return self.dependency_state.time_window

    @time_window.setter
    def time_window(self, value: Dict[str, Any]) -> None:
        self.dependency_state.time_window = value
        self.dependency_state.mark_resolved("time_window")

    @property
    def schema(self) -> Optional[Dict[str, Any]]:
        return self.dependency_state.schema

    @schema.setter
    def schema(self, value: Dict[str, Any]) -> None:
        self.dependency_state.schema = value
        self.dependency_state.mark_resolved("schema")


@dataclass
class SQLGenerationResult:
    """Structured result returned by the coordinator."""

    success: bool
    sql: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    needs_user_input: bool = False
    suggestions: Optional[List[str]] = None
    debug_info: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def success_result(cls, sql: str, metadata: Optional[Dict[str, Any]] = None) -> "SQLGenerationResult":
        return cls(success=True, sql=sql, metadata=metadata or {})

    @classmethod
    def failed_result(
        cls,
        error: str,
        debug_info: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SQLGenerationResult":
        return cls(success=False, error=error, debug_info=debug_info, metadata=metadata or {})

    @classmethod
    def user_input_required(
        cls,
        message: str,
        suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SQLGenerationResult":
        return cls(
            success=False,
            error=message,
            needs_user_input=True,
            suggestions=suggestions,
            metadata=metadata or {},
        )
