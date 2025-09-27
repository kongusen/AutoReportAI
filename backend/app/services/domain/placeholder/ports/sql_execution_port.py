"""
SQL Execution Port (Domain Port)

Executes SQL against a configured data source and returns tabular results.
Implementations belong to Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SqlExecutionPort(ABC):
    @abstractmethod
    async def execute(self, sql: str, data_source_id: str) -> QueryResult:
        pass

