"""
SQL Execution Adapter (Infrastructure)

Implements Domain SqlExecutionPort by delegating to the unified data query
executor (connectors via QueryExecutorService).
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.domain.placeholder.ports.sql_execution_port import SqlExecutionPort, QueryResult
from app.services.data.query.query_executor_service import query_executor_service


class SqlExecutionAdapter(SqlExecutionPort):
    async def execute(self, sql: str, data_source_id: str) -> QueryResult:
        # Delegate to QueryExecutorService which handles connectors and safety
        params: Dict[str, Any] = {"data_source_id": data_source_id}
        result = await query_executor_service.execute_query(sql, params)

        # Map result to Domain QueryResult
        columns = result.get("metadata", {}).get("columns") or []
        data = result.get("data") or []
        rows = [[rec.get(col) for col in columns] for rec in data] if columns else [list(rec.values()) for rec in data]
        row_count = result.get("metadata", {}).get("row_count")
        if row_count is None:
            row_count = len(rows)
        metadata = {
            "query": result.get("metadata", {}).get("query"),
            "execution_time": result.get("metadata", {}).get("execution_time"),
            "data_source": result.get("metadata", {}).get("data_source"),
            "success": result.get("success", False),
            "error": result.get("error"),
        }
        return QueryResult(columns=columns, rows=rows, row_count=row_count, metadata=metadata)
