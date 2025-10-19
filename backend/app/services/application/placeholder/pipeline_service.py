"""
占位符流水线应用服务

把 Domain 的扫描/处理/替换 串入应用层编排：
- ETL 前扫描：识别统计/图表占位符并标记重分析
- 报告组装：通过端口生成SQL并执行/渲染，替换占位符并附20字说明
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.services.domain.placeholder.usecases.scanner import PlaceholderScanner
from app.services.domain.placeholder.usecases.replacer import ReportReplacer
from app.services.domain.placeholder.core.handlers.period_handler import PeriodHandler
from app.services.domain.placeholder.ports.sql_generation_port import QuerySpec, SchemaContext, TimeWindow
from app.services.infrastructure.agents.adapters.schema_discovery_adapter import SchemaDiscoveryAdapter
from app.services.infrastructure.agents.adapters.sql_generation_adapter import SqlGenerationAdapter
from app.services.infrastructure.agents.adapters.sql_execution_adapter import SqlExecutionAdapter
from app.services.infrastructure.agents.adapters.chart_rendering_adapter import ChartRenderingAdapter

from app.crud import template as crud_template
from app.db.session import get_db_session


class PlaceholderPipelineService:
    def __init__(self) -> None:
        self._schema = SchemaDiscoveryAdapter()
        self._sql_gen = SqlGenerationAdapter()
        self._sql_exec = SqlExecutionAdapter()
        self._chart = ChartRenderingAdapter()
        self._scanner = PlaceholderScanner(self._schema)
        self._replacer = ReportReplacer()
        self._period = PeriodHandler()

    async def etl_pre_scan(self, template_id: str, data_source_id: str) -> Dict[str, Any]:
        content = self._load_template_content(template_id)
        items = await self._scanner.scan_template(template_id, content, data_source_id)
        stats = {
            "total": len(items),
            "need_reanalysis": sum(1 for i in items if i.needs_reanalysis),
            "by_kind": {
                "period": len([i for i in items if i.kind == "period"]),
                "statistical": len([i for i in items if i.kind == "statistical"]),
                "chart": len([i for i in items if i.kind == "chart"]),
            }
        }
        return {"success": True, "items": [i.__dict__ for i in items], "stats": stats}

    async def assemble_report(self, template_id: str, data_source_id: str, *, user_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, schedule: Optional[Dict[str, Any]] = None, execution_time: Optional[str] = None) -> Dict[str, Any]:
        content = self._load_template_content(template_id)
        # 时间上下文：优先使用调度表达式生成周期
        from app.utils.time_context import TimeContextManager
        tm = TimeContextManager()
        time_ctx: Dict[str, Any]
        if schedule and schedule.get('cron_expression'):
            ctx = tm.build_task_time_context(schedule['cron_expression'], datetime.fromisoformat(execution_time) if execution_time else None)
            time_ctx = {
                "cron_expression": schedule['cron_expression'],
                "execution_time": execution_time or ctx.get('execution_time'),
                "schedule": schedule,
                "start_date": ctx.get('data_start_time'),
                "end_date": ctx.get('data_end_time'),
            }
        else:
            if not end_date:
                end_date = datetime.utcnow().date().isoformat()
            if not start_date:
                start_date = (datetime.utcnow().date() - timedelta(days=7)).isoformat()
            time_ctx = {"start_date": start_date, "end_date": end_date}

        # Schema
        sc = await self._schema.introspect(data_source_id)
        schema_ctx = SchemaContext(tables=sc.tables, columns=sc.columns)

        # 扫描占位符
        items = await self._scanner.scan_template(template_id, content, data_source_id)

        # 逐个生成/执行
        resolved: Dict[str, Dict[str, Any]] = {}
        chart_artifacts: List[str] = []
        for it in items:
            name = it.text  # raw inside {{ ... }}
            kind = it.kind
            if kind == "period":
                period = await self._period.compute(name, time_ctx)
                resolved[name] = {"kind": "period", **period}
                continue
            # build query spec and time window
            q = QuerySpec(intent=name)
            tw = TimeWindow(start_date=start_date, end_date=end_date, granularity="daily")
            # generate SQL (pass ds id and user_id to business ctx for fallback introspect)
            gen = await self._sql_gen.generate_sql(q, schema_ctx, tw, business_ctx={"data_source_id": data_source_id, "template_id": template_id, "user_id": user_id})
            sql = gen.sql or "SELECT 1 AS stub"
            exec_res = await self._sql_exec.execute(sql, data_source_id)
            if kind == "chart":
                art = await self._chart.render(spec=None, data_columns=exec_res.columns, data_rows=exec_res.rows)  # adapter tolerates None spec
                resolved[name] = {
                    "kind": "chart",
                    "rows": exec_res.rows,
                    "columns": exec_res.columns,
                    "artifact": art.path,
                    "chart_type": "bar",
                }
                chart_artifacts.append(art.path)
            else:
                # statistical: pick a value heuristically
                value = None
                try:
                    if exec_res.rows and exec_res.columns:
                        value = exec_res.rows[0][0]
                except Exception:
                    value = None
                resolved[name] = {
                    "kind": "statistical",
                    "value": value,
                    "columns": exec_res.columns,
                    "rows": exec_res.rows,
                    "metric": (exec_res.columns[0] if exec_res.columns else "结果")
                }

        # 替换
        assembled = await self._replacer.replace(content, {"time": time_ctx}, resolved)
        return {"success": True, "content": assembled, "artifacts": chart_artifacts, "resolved": resolved}

    def _load_template_content(self, template_id: str) -> str:
        with get_db_session() as db:
            tpl = crud_template.get(db, id=template_id)
            if not tpl:
                raise ValueError("模板不存在")
            # 支持两种存储
            if getattr(tpl, 'content', None):
                return tpl.content
            if getattr(tpl, 'file_path', None):
                try:
                    with open(tpl.file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception:
                    pass
            raise ValueError("无法读取模板内容")
