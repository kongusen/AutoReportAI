"""Agent system dataclasses covering both legacy and Loom runtimes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Legacy structures (kept for compatibility with existing services)
# ---------------------------------------------------------------------------


@dataclass
class PlaceholderSpec:
    id: Optional[str] = None
    description: str = ""
    type: str = "stat"  # "stat", "chart", "list", "text"
    granularity: str = "daily"  # "daily", "weekly", "monthly"


@dataclass
class SchemaInfo:
    tables: List[str] = field(default_factory=list)
    columns: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class TaskContext:
    task_time: Optional[float] = None
    timezone: str = "Asia/Shanghai"
    window: Optional[Dict[str, Any]] = None


@dataclass
class AgentConstraints:
    sql_only: bool = True
    output_kind: str = "sql"  # "sql", "chart", "report"
    max_attempts: int = 5
    policy_row_limit: Optional[int] = None
    quality_min_rows: Optional[int] = None


@dataclass
class AgentInput:
    user_prompt: str
    placeholder: PlaceholderSpec
    schema: SchemaInfo
    context: TaskContext
    constraints: AgentConstraints = field(default_factory=AgentConstraints)
    template_id: Optional[str] = None
    data_source: Optional[Dict[str, Any]] = None
    task_driven_context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


@dataclass
class AgentOutput:
    success: bool
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)


ToolResult = Dict[str, Any]


# ---------------------------------------------------------------------------
# Loom-specific request/response wrappers
# ---------------------------------------------------------------------------


@dataclass
class AgentRequest:
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    mode: str = "template"
    stage: str = "template"


@dataclass
class AgentResponse:
    success: bool
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


__all__ = [
    "PlaceholderSpec",
    "SchemaInfo",
    "TaskContext",
    "AgentConstraints",
    "AgentInput",
    "AgentOutput",
    "ToolResult",
    "AgentRequest",
    "AgentResponse",
]
