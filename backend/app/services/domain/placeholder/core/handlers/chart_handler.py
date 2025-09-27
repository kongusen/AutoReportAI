"""
Chart Placeholder Handler (Domain)

Generates SQL, executes it, and renders a chart artifact.
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.domain.placeholder.ports.sql_generation_port import (
    SqlGenerationPort, QuerySpec, SchemaContext, TimeWindow,
)
from app.services.domain.placeholder.ports.sql_execution_port import SqlExecutionPort
from app.services.domain.placeholder.ports.chart_rendering_port import ChartRenderingPort, ChartSpec


class ChartHandler:
    def __init__(self, sql_gen: SqlGenerationPort, sql_exec: SqlExecutionPort, chart: ChartRenderingPort) -> None:
        self._gen = sql_gen
        self._exec = sql_exec
        self._chart = chart

    async def analyze_and_render(
        self,
        placeholder_text: str,
        schema: Dict[str, Any],
        time_ctx: Dict[str, Any],
        data_source_id: str,
        chart_type: str = "bar",
    ) -> Dict[str, Any]:
        query = QuerySpec(intent=placeholder_text)
        schema_ctx = SchemaContext(tables=schema.get("tables", []), columns=schema.get("columns", {}))
        tw = TimeWindow(start_date=time_ctx.get("start_date") or time_ctx.get("data_start_date"), end_date=time_ctx.get("end_date") or time_ctx.get("data_end_date"))
        sql_res = await self._gen.generate_sql(query, schema_ctx, tw, business_ctx={"data_source_id": data_source_id})
        exec_res = await self._exec.execute(sql_res.sql, data_source_id)
        spec = ChartSpec(chart_type=chart_type)
        artifact = await self._chart.render(spec, exec_res.columns, exec_res.rows)
        return {
            "sql": sql_res.sql,
            "columns": exec_res.columns,
            "rows": exec_res.rows,
            "artifact": artifact.path,
            "artifact_meta": {"mime": artifact.mime_type, "w": artifact.width, "h": artifact.height},
        }
