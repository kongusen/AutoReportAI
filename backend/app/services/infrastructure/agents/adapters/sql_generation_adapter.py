"""
SQL Generation Adapter (Infrastructure)

Implements Domain SqlGenerationPort by delegating to the existing Agent system
or other rule-based generators.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.domain.placeholder.ports.sql_generation_port import (
    SqlGenerationPort, QuerySpec, SchemaContext, TimeWindow, SqlGenerationResult,
)
from app.services.infrastructure.agents.adapters.schema_discovery_adapter import SchemaDiscoveryAdapter


class SqlGenerationAdapter(SqlGenerationPort):
    def __init__(self) -> None:
        # could accept a facade or container if needed
        pass

    async def generate_sql(
        self,
        query: QuerySpec,
        schema: SchemaContext,
        time: Optional[TimeWindow] = None,
        business_ctx: Optional[Dict[str, Any]] = None,
    ) -> SqlGenerationResult:
        try:
            # Lazy import to avoid hard coupling in Domain
            from app.services.infrastructure.agents.facade import AgentFacade
            from app.services.infrastructure.agents.types import (
                AgentInput, PlaceholderSpec as APS, SchemaInfo as ASI,
                TaskContext as ATC, AgentConstraints
            )
            from app.core.container import Container

            # Ensure schema is available; if empty and have data_source_id, introspect
            if (not schema.tables or not schema.columns) and business_ctx and business_ctx.get("data_source_id"):
                print(f"🔍 Schema为空，尝试introspect数据源: {business_ctx.get('data_source_id')}")
                try:
                    introspector = SchemaDiscoveryAdapter()
                    sc = await introspector.introspect(business_ctx["data_source_id"])
                    original_tables = len(schema.tables)
                    original_columns = len(schema.columns)
                    schema = SchemaContext(tables=sc.tables, columns=sc.columns)
                    print(f"✅ Schema introspect成功: {original_tables}->{len(schema.tables)} 表, "
                          f"{original_columns}->{len(schema.columns)} 列集合")
                except Exception as e:
                    print(f"❌ Schema introspect失败: {e}")
                    import traceback
                    print(f"❌ 详细错误: {traceback.format_exc()}")

            # Parse semantic hints from query intent if possible
            semantic_type, top_n = self._infer_semantics(query.intent)

            # Build technical prompt from structured query
            time_hint = ""
            if time and (time.start_date or time.end_date):
                time_hint = f" 时间范围: {time.start_date or ''}~{time.end_date or ''}."
            measures = ", ".join(query.measures) if query.measures else ""
            dims = ", ".join(query.dimensions) if query.dimensions else ""
            filters_desc = "; ".join([
                f"{f.get('field', '')} {f.get('op', '')} {f.get('value', '')}"
                for f in (query.filters or [])
            ]) if query.filters else ""
            group_by_desc = ", ".join(query.group_by) if query.group_by else dims
            order_by_desc = ", ".join([
                f"{o.get('field')} {o.get('dir', 'desc')}"
                for o in (query.order_by or [])
            ])
            guidance_extra = []
            if semantic_type == "ranking":
                guidance_extra.append(f"按度量降序排序并取前{top_n or 'N'}")
            if semantic_type == "compare":
                guidance_extra.append("输出基准、对比、差值与百分比变化列")
            guidance_extra.append("为大表添加时间过滤或LIMIT，避免全表扫描")
            guidance = "\n- ".join(guidance_extra)

            user_prompt = (
                f"根据需求生成可执行SQL。\n"
                f"需求: {query.intent}.{time_hint}\n"
                f"分组维度: {dims or group_by_desc}\n"
                f"度量: {measures or '自动推断'}\n"
                f"筛选: {filters_desc or '无'}\n"
                f"排序: {order_by_desc or '适配需求'}\n"
                f"限制: {query.limit or '按策略限制'}\n"
                f"- {guidance}"
                f"\n只返回SQL，不要解释。"
            ).strip()

            # 构建AgentInput并记录详细信息
            schema_info = ASI(tables=schema.tables, columns=schema.columns)
            print(f"🤖 构建AgentInput - schema: {len(schema_info.tables)} 表, {len(schema_info.columns)} 列集合")
            print(f"🤖 Schema tables: {schema_info.tables[:3]}{'...' if len(schema_info.tables) > 3 else ''}")
            for table in list(schema_info.columns.keys())[:2]:
                cols = schema_info.columns[table]
                print(f"🤖 表 {table}: {len(cols)} 列 {cols[:5]}{'...' if len(cols) > 5 else ''}")

            ai = AgentInput(
                user_prompt=user_prompt,
                placeholder=APS(
                    id="sql_gen",
                    description=query.intent,
                    type="stat",
                    granularity=time.granularity if time else "daily"
                ),
                schema=schema_info,
                context=ATC(
                    task_time=None,
                    timezone="Asia/Shanghai",
                    window={
                        "start_date": time.start_date if time else None,
                        "end_date": time.end_date if time else None
                    }
                ),
                constraints=AgentConstraints(
                    sql_only=True,
                    output_kind="sql",
                    max_attempts=3,
                    policy_row_limit=5000,
                    quality_min_rows=10
                ),
                template_id=business_ctx.get("template_id") if business_ctx else None,
                data_source={
                    "data_source_id": business_ctx.get("data_source_id")
                } if business_ctx and business_ctx.get("data_source_id") else None,
                task_driven_context={
                    "placeholder_contexts": [
                        {
                            "placeholder_name": query.intent[:60],
                            "semantic_type": semantic_type,
                            "parsed_params": {"top_n": top_n},
                        }
                    ]
                },
            )

            print(f"🤖 AgentInput构建完成: semantic_type={semantic_type}, top_n={top_n}")

            facade = AgentFacade(Container())
            out = await facade.execute(ai)
            sql_text = out.result if out and out.success else ""
            quality_score = (
                out.metadata.get("quality_score", 0.0)
                if out and out.metadata else 0.0
            )
            reasoning = (out.metadata or {}).get("reasoning")
            return SqlGenerationResult(
                sql=sql_text,
                quality_score=quality_score,
                reasoning=reasoning
            )
        except Exception:
            # Fallback stub keeps system running; use a harmless SELECT
            sql = "SELECT 1 AS stub"
            return SqlGenerationResult(sql=sql, quality_score=0.0, reasoning="fallback_stub")

    def _infer_semantics(self, intent: str) -> tuple[str, Optional[int]]:
        t = (intent or "").lower()
        # ranking detection
        import re
        top_n = None
        m = re.search(r"top\s*(\d+)", t)
        if m:
            top_n = int(m.group(1))
            return ("ranking", top_n)
        for kw in ["排名", "前", "top", "排行"]:
            if kw in intent:
                top_n = top_n or None
                return ("ranking", top_n)
        for kw in ["同比", "环比", "对比", "compare", "vs", "差值"]:
            if kw in intent:
                return ("compare", None)
        return (None, None)
