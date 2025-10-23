"""
Agent Input Bridge (Application Layer)

一键式接口：统一上下文 -> AgentInput -> (可选) 执行Agent

职责：
- 调用 ContextCoordinator 构建真实上下文（无mock）
- 通过 ContextCoordinator.build_agent_input 生成标准 AgentInput
- 动态 user_prompt 结合模板语境、时间指令、业务规则与schema摘要
- 可选：直接调用 AgentFacade 执行 PTOF 流程，返回 AgentOutput
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from ..context import ContextCoordinator
from .builder import AgentInputBuilder

logger = logging.getLogger(__name__)


class AgentInputBridge:
    """应用层桥接服务：上下文 -> AgentInput / Agent 执行"""

    def __init__(self, container=None) -> None:
        # Default to a new container if none provided
        if container is None:
            from app.core.container import Container
            container = Container()

        self.container = container
        self._coordinator = ContextCoordinator(container)

    async def build_for_placeholder(
        self,
        *,
        user_id: str,
        template_id: str,
        data_source_id: str,
        placeholder_name: str,
        task_definition: Dict[str, Any],
        output_kind: str = "sql",
        sql_only: bool = True,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """基于统一上下文构造 AgentInput（不执行Agent）。"""
        # 1) 构建完整上下文
        context = await self._coordinator.build_full_context(
            user_id=user_id,
            template_id=template_id,
            data_source_id=data_source_id,
            task_definition=task_definition,
            force_refresh=force_refresh,
        )

        # 2) 桥接为 AgentInput
        bridged = AgentInputBuilder(self.container).build(
            context,
            placeholder_name=placeholder_name,
            output_kind=output_kind,
            sql_only=sql_only,
            user_id=user_id,
        )

        return {
            "success": context.success,
            "errors": context.errors,
            "warnings": context.warnings,
            "context_id": context.context_id,
            "agent_input": bridged["agent_input"],
            "dynamic_user_prompt": bridged["dynamic_user_prompt"],
            "meta": bridged.get("meta", {}),
            "agent_context": context.to_agent_format(),
            "consolidated_context": context.get_consolidated_context(),
        }

    async def execute_for_placeholder(
        self,
        *,
        user_id: str,
        template_id: str,
        data_source_id: str,
        placeholder_name: str,
        task_definition: Dict[str, Any],
        output_kind: str = "sql",
        sql_only: bool = True,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """基于统一上下文构造 AgentInput 并执行 Agent（PTOF）。"""
        # 1) 构造 AgentInput
        build_res = await self.build_for_placeholder(
            user_id=user_id,
            template_id=template_id,
            data_source_id=data_source_id,
            placeholder_name=placeholder_name,
            task_definition=task_definition,
            output_kind=output_kind,
            sql_only=sql_only,
            force_refresh=force_refresh,
        )

        ai = build_res.get("agent_input")
        if not ai:
            return {
                "success": False,
                "error": "agent_input_build_failed",
                "build_result": build_res,
            }

        # 2) 执行 Agent（PTOF）
        try:
            from app.services.infrastructure.agents import AgentService
            from app.core.container import Container

            container = self.container or Container()
            service = AgentService(container=container)
            result = await service.execute(ai)

            return {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
                "stage": build_res.get("meta", {}).get("stage"),
                "available_tools": build_res.get("meta", {}).get("available_tools"),
                "dynamic_user_prompt": build_res.get("dynamic_user_prompt"),
                "context_id": build_res.get("context_id"),
                "agent_context": build_res.get("agent_context"),
            }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "build_result": build_res,
            }
