from __future__ import annotations

from typing import Any, Dict, List


class AgentInputBuilder:
    """将统一上下文(Context)转换为 AgentInput 的构建器。

    说明：为保持分层清晰，构建逻辑集中在本类；ContextCoordinator 可委托调用本类。
    """

    def __init__(self, container=None) -> None:
        self.container = container

    def build(
        self,
        context,
        placeholder_name: str,
        *,
        output_kind: str = "sql",
        sql_only: bool = True,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        """从 Context 对象构建 AgentInput 与动态prompt。"""
        from app.services.infrastructure.agents.types import (
            AgentInput as _AgentInput,
            PlaceholderSpec as _PlaceholderSpec,
            SchemaInfo as _SchemaInfo,
            TaskContext as _AgentTaskContext,
            AgentConstraints as _AgentConstraints,
        )
        from app.services.infrastructure.agents.planner import AgentPlanner

        consolidated = context.get_consolidated_context()

        # 1) schema
        db_ctx = consolidated.get("database_context") or {}
        tables_list, columns_map, schema_meta = self._extract_schema(db_ctx)

        # 2) time/window
        time_ctx = consolidated.get("time_context") or {}
        timezone = time_ctx.get("timezone") or "Asia/Shanghai"
        window = time_ctx

        # 3) 占位符规范与动态prompt
        ph_spec, ph_meta = self._derive_placeholder_spec(consolidated, placeholder_name)
        # 使用类型感知的 PromptComposer 生成动态提示词
        try:
            from .prompt_templates import PromptComposer
            dynamic_user_prompt = PromptComposer().compose(
                consolidated, placeholder_name, output_kind, ph_meta
            )
        except Exception:
            # 回退到内置简易模板
            dynamic_user_prompt = self._compose_dynamic_user_prompt(
                consolidated, placeholder_name, output_kind, ph_meta
            )

        constraints = _AgentConstraints(
            sql_only=(sql_only if output_kind == "sql" else False),
            output_kind=output_kind,
        )

        # 4) data source normalization
        ds_norm: Dict[str, Any] = {}
        tdc_ds = consolidated.get("data_source") or {}
        if tdc_ds:
            # Normalize type to connector types
            src_type = (tdc_ds.get("type") or "").lower()
            type_map = {
                "mysql": "sql",
                "postgres": "sql",
                "postgresql": "sql",
                "mariadb": "sql",
            }
            norm_type = type_map.get(src_type, src_type)
            ds_norm = {
                "id": tdc_ds.get("id"),
                "type": norm_type or None,
                "database": tdc_ds.get("database")
            }
        else:
            # Fallback to database_context
            ds_norm = {
                "database": db_ctx.get("database_name"),
                "type": (db_ctx.get("database_type") or "").lower() or None,
            }

        ai = _AgentInput(
            user_prompt=dynamic_user_prompt,
            placeholder=_PlaceholderSpec(
                id=ph_spec.get("id"),
                description=ph_spec.get("description", placeholder_name),
                type=ph_spec.get("type", "stat"),
                granularity=ph_spec.get("granularity", "daily"),
            ),
            schema=_SchemaInfo(tables=tables_list, columns=columns_map),
            context=_AgentTaskContext(task_time=None, timezone=timezone, window=window),
            constraints=constraints,
            template_id=str(consolidated.get("template_info", {}).get("id", "")) or None,
            data_source=ds_norm,
            task_driven_context=consolidated,
            user_id=user_id,  # 传递真实的用户ID
        )

        # 推断阶段与可用工具（不触发LLM）
        stage = None
        available_tools = []
        try:
            planner = AgentPlanner(self.container)
            stage = planner._infer_stage(ai)  # type: ignore[attr-defined]
            available_tools = planner._get_available_tools(stage)  # type: ignore[attr-defined]
        except Exception:
            pass

        return {
            "agent_input": ai,
            "dynamic_user_prompt": dynamic_user_prompt,
            "meta": {
                "user_id": user_id,
                "placeholder": ph_meta,
                "schema_summary": schema_meta,
                "time_context": time_ctx,
                "stage": getattr(stage, "value", None),
                "available_tools": available_tools,
            },
        }

    def _extract_schema(self, db_ctx: Dict[str, Any]):
        tables: List[str] = []
        columns: Dict[str, List[str]] = {}
        meta = {"tables": 0, "columns": 0, "samples": []}

        for t in db_ctx.get("tables", []) or []:
            name = t.get("table_name")
            if not name:
                continue
            tables.append(name)
            cols = [c.get("name") for c in (t.get("columns") or []) if c.get("name")]
            columns[name] = cols
            meta["samples"].append({"table": name, "columns_preview": cols[:5]})

        meta["tables"] = len(tables)
        meta["columns"] = sum(len(v) for v in columns.values())
        return tables, columns, meta

    def _derive_placeholder_spec(self, consolidated: Dict[str, Any], placeholder_name: str):
        tpl_ctx = consolidated.get("placeholder_contexts") or []
        ph = None
        for item in tpl_ctx:
            if item.get("placeholder_name") == placeholder_name:
                ph = item
                break

        type_map = {"统计类": "stat", "图表类": "chart", "周期类": "period"}
        ph_type = (ph or {}).get("semantic_type") or type_map.get((ph or {}).get("type"), "stat")

        # 名称关键词细化：ranking / compare
        name = placeholder_name or ""
        name_lower = name.lower()
        if any(k in name for k in ["同比", "环比"]) or any(k in name_lower for k in ["yoy", "mom", "compare"]):
            ph_type = "compare"
        else:
            if any(k in name for k in ["排名", "排行", "最高", "最低", "榜"]) or "top" in name_lower:
                ph_type = "ranking"
            else:
                # 简单识别“前/后N”
                import re
                if re.search(r"(前|后)\s*\d+", name):
                    ph_type = "ranking"
        desc = (ph or {}).get("context_paragraph") or f"占位符 {placeholder_name}"
        spec = {"id": placeholder_name, "description": desc, "type": ph_type, "granularity": "daily"}
        top_n = None
        try:
            top_n = (ph or {}).get("parsed_params", {}).get("top_n")
        except Exception:
            top_n = None
        if top_n is None:
            # 回退：从名称中尝试解析 Top N
            import re
            m = re.search(r"top\s*(\d+)", (placeholder_name or ""), flags=re.IGNORECASE)
            if m:
                try:
                    top_n = int(m.group(1))
                except Exception:
                    top_n = None
        meta = {
            "name": placeholder_name,
            "type_cn": (ph or {}).get("type"),
            "type": ph_type,
            "position": (ph or {}).get("position_info"),
            "top_n": top_n,
        }
        return spec, meta

    def _compose_dynamic_user_prompt(
        self,
        consolidated: Dict[str, Any],
        placeholder_name: str,
        output_kind: str,
        ph_meta: Dict[str, Any],
    ) -> str:
        template_info = consolidated.get("template_info", {})
        time_ctx = consolidated.get("time_context", {})
        rules = consolidated.get("business_rules", [])

        db_ctx = consolidated.get("database_context") or {}
        tables = [t.get("table_name") for t in (db_ctx.get("tables") or []) if t.get("table_name")]
        tables_str = ", ".join(tables[:5]) + ("..." if len(tables) > 5 else "") if tables else "无"

        goal = f"为占位符《{placeholder_name}》生成{('SQL' if output_kind=='sql' else '所需结果')}"
        if output_kind == "chart":
            goal = f"为占位符《{placeholder_name}》生成图表所需的数据SQL与图表配置"
        elif output_kind == "report":
            goal = f"为占位符《{placeholder_name}》生成报告段落所需的数据与文本"

        time_hint = time_ctx.get("agent_instructions") or ""
        rules_hint = ("\n- ".join(rules)) if rules else ""

        lines = [
            f"任务: {goal}",
            f"模板: {template_info.get('name') or template_info.get('id') or ''}",
            f"语境: {ph_meta.get('type_cn') or ph_meta.get('type') or ''}",
            f"可用表: {tables_str}",
        ]
        if time_hint:
            lines.append(f"时间指令: {time_hint.strip()}")
        if rules_hint:
            lines.append(f"业务规则:\n- {rules_hint}")

        return "\n".join([l for l in lines if l])
