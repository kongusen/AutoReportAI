"""
Statistical Placeholder Handler (Domain)

Generates SQL (via port), executes (via port), and returns data + metadata.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.domain.placeholder.ports.sql_generation_port import (
    SqlGenerationPort, QuerySpec, SchemaContext, TimeWindow,
)
from app.services.domain.placeholder.ports.sql_execution_port import SqlExecutionPort


class StatisticalHandler:
    def __init__(self, sql_gen: SqlGenerationPort, sql_exec: SqlExecutionPort) -> None:
        self._gen = sql_gen
        self._exec = sql_exec

    async def analyze_and_fetch(
        self,
        placeholder_text: str,
        schema: Dict[str, Any],
        time_ctx: Dict[str, Any],
        data_source_id: str,
    ) -> Dict[str, Any]:
        query = QuerySpec(intent=placeholder_text)
        schema_ctx = SchemaContext(tables=schema.get("tables", []), columns=schema.get("columns", {}))
        tw = TimeWindow(start_date=time_ctx.get("start_date") or time_ctx.get("data_start_date"), end_date=time_ctx.get("end_date") or time_ctx.get("data_end_date"))
        sql_res = await self._gen.generate_sql(query, schema_ctx, tw, business_ctx={"data_source_id": data_source_id})
        exec_res = await self._exec.execute(sql=sql_res.sql, connection_config={"data_source_id": data_source_id})
        return {
            "sql": sql_res.sql,
            "columns": exec_res.columns,
            "rows": exec_res.rows,
            "meta": {"quality": sql_res.quality_score},
        }
