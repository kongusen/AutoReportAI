"""
AI Content Adapter (Infrastructure)

Implements AiContentPort using the existing Agent system. Builds minimal
technical prompts and delegates to execute_agent_task compat wrapper.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.domain.placeholder.ports.ai_content_port import AiContentPort


class AiContentAdapter(AiContentPort):
    async def generate_placeholder_content(
        self,
        *,
        placeholder_name: str,
        placeholder_type: str,
        description: str,
        data_source_id: str,
        task_id: Optional[str] = None,
        template_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            from app.services.infrastructure.agents import execute_agent_task
            context = {
                "placeholders": {
                    "placeholder_name": placeholder_name,
                    "placeholder_type": placeholder_type,
                    "placeholder_description": description,
                    "data_source_id": str(data_source_id),
                    "task_id": str(task_id) if task_id else None,
                    "template_id": str(template_id) if template_id else None,
                }
            }
            if extra:
                context.update(extra)
            result = await execute_agent_task(
                task_name="内容生成",
                task_description=f"为占位符 {placeholder_name} 生成报告内容",
                context_data=context,
                user_id=(extra or {}).get("user_id", "system"),
            )
            if result and result.get("success"):
                content = result.get("result") or ""
                if isinstance(content, dict):
                    return content.get("generated_content", "")
                return str(content)
        except Exception:
            pass
        return ""

    async def interpret_placeholder(
        self,
        *,
        placeholder_name: str,
        placeholder_type: str,
        description: str,
        analysis_results: Dict[str, Any],
        target_audience: str = "business",
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            from app.services.infrastructure.agents import execute_agent_task
            context = {
                "placeholders": {
                    "placeholder_name": placeholder_name,
                    "placeholder_type": placeholder_type,
                    "placeholder_description": description,
                    "analysis_results": analysis_results,
                    "target_audience": target_audience,
                }
            }
            if extra:
                context.update(extra)
            result = await execute_agent_task(
                task_name="业务洞察解释",
                task_description=f"解释模板占位符 '{placeholder_name}' 的业务含义",
                context_data=context,
                user_id=(extra or {}).get("user_id", "system"),
            )
            if result and result.get("success"):
                content = result.get("result") or ""
                if isinstance(content, dict):
                    return content.get("interpretation", "")
                return str(content)
        except Exception:
            pass
        return ""

