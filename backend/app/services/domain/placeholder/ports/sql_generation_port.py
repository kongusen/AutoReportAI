"""
SQL Generation Port (Domain Port)

Defines the business-facing interface for generating SQL from structured
placeholder requirements and structured contexts. Implementations live in
Infrastructure as Adapters (e.g., Agents/LLM/Rule-based).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuerySpec:
    """Structured query requirements derived from placeholder spec."""
    intent: str                 # e.g., "count complaints by day"
    measures: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    order_by: List[Dict[str, str]] = field(default_factory=list)  # {field, dir}
    limit: Optional[int] = None
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaContext:
    """Minimal schema information required for SQL generation."""
    tables: List[str]
    columns: Dict[str, List[str]]


@dataclass
class TimeWindow:
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    granularity: Optional[str] = None  # daily|weekly|monthly


@dataclass
class SqlGenerationResult:
    sql: str
    quality_score: float = 0.0
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SqlGenerationPort(ABC):
    """Domain Port for generating SQL from structured inputs."""

    @abstractmethod
    async def generate_sql(
        self,
        query: QuerySpec,
        schema: SchemaContext,
        time: Optional[TimeWindow] = None,
        business_ctx: Optional[Dict[str, Any]] = None,
    ) -> SqlGenerationResult:
        pass

