"""
AI SQL Repair Adapter (Infrastructure)

Implements the Domain AiSqlRepairPort by calling the existing Agent system's
compat wrapper `execute_agent_task`, composing a technical prompt that enforces
dynamic time expressions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from app.services.domain.placeholder.ports.ai_sql_repair_port import AiSqlRepairPort


class AiSqlRepairAdapter(AiSqlRepairPort):
    async def repair_sql(
        self,
        *,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        original_sql: str,
        error_message: str,
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        try:
            # Lazy import to avoid top-level circulars
            from app.services.infrastructure.agents import execute_agent_task

            prompt = self._build_prompt(error_message, time_context)

            placeholder_dict = {
                "id": placeholder_name,
                "description": placeholder_text,
                "type": "stat",
                "granularity": "daily",
            }
            context = {
                "user_prompt": prompt,
                "template_id": template_id,
                "timezone": time_context.get("timezone", "Asia/Shanghai") if time_context else "Asia/Shanghai",
                "task_params": {
                    "original_sql": original_sql,
                    "error_message": error_message,
                    "repair_mode": True,
                    "validation_mode": True,
                    "dynamic_time_required": True,
                    "time_context": time_context or {},
                },
            }

            schema = {
                "tables": data_source_info.get("tables", []),
                "columns": data_source_info.get("columns", {}),
            }

            result = await execute_agent_task(
                placeholder=placeholder_dict,
                context=context,
                schema=schema,
                user_id=user_id,
            )

            if result and result.get("success"):
                raw_sql = result.get("sql") or result.get("result")
                return raw_sql or None
            return None

        except Exception:
            return None

    def _build_prompt(self, error_message: str, time_context: Optional[Dict[str, Any]]) -> str:
        # Technical, implementation-specific prompt (keep in Infra)
        fixed_guidance = (
            "重要：生成的SQL必须使用动态时间范围，不能写死固定日期。使用相对时间表达式：\n"
            "- CURDATE() - INTERVAL 1 DAY （前一天）\n"
            "- DATE_SUB(CURDATE(), INTERVAL 1 DAY) （前一天）\n"
            "- DATE_FORMAT(CURDATE() - INTERVAL 1 DAY, '%Y-%m-%d') （格式化）\n"
        )
        time_info = ""
        if time_context:
            start = time_context.get("data_start_date") or time_context.get("start_date")
            end = time_context.get("data_end_date") or time_context.get("end_date")
            time_info = f"\n时间范围参考: {start} 到 {end}\n" if (start or end) else "\n"

        return (
            f"SQL修复任务 - 原SQL执行失败: {error_message}\n\n"
            f"{fixed_guidance}"
            f"请基于错误信息修复查询，保持原有意图不变。"
            f"{time_info}"
        )

