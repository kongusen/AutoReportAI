"""
Stage-aware agent adapter

提供一个面向应用层的轻量封装，统一调用 StageAwareFacade 的
SQL / 图表 / 文档三个阶段能力，屏蔽细节并返回结构化结果。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from app.core.container import Container
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.infrastructure.agents import (
        AgentResponse,
        StageAwareFacade,
        TaskComplexity,
        create_stage_aware_facade,
    )

logger = logging.getLogger(__name__)


class StageAwareAgentAdapter:
    """Stage-Aware Facade 的应用层适配器。"""

    def __init__(
        self,
        *,
        container: Optional[Container] = None,
        enable_stage_aware: bool = True,
    ) -> None:
        self._container = container or Container()
        self._enable_stage_aware = enable_stage_aware

        self._facade: Optional["StageAwareFacade"] = None
        self._facade_user_id: Optional[str] = None
        self._facade_task_type: Optional[str] = None
        self._initialized: bool = False
        
        # TT 递归上下文管理
        self._turn_counter: int = 0
        self._shared_context: Dict[str, Any] = {}

    async def initialize(
        self,
        *,
        user_id: str,
        task_type: str,
        task_complexity: "TaskComplexity" = None,
    ) -> None:
        """
        初始化（或重新初始化）StageAwareFacade。

        如果 user_id 或 task_type 发生变化，会重新创建 Facade，
        以确保每次都使用正确的用户配置。
        """
        # 动态导入以避免循环依赖
        from app.services.infrastructure.agents import (
            TaskComplexity,
            create_stage_aware_facade,
        )
        
        if task_complexity is None:
            task_complexity = TaskComplexity.MEDIUM
            
        should_recreate = (
            self._facade is None
            or self._facade_user_id != user_id
            or self._facade_task_type != task_type
        )

        if should_recreate:
            self._facade = create_stage_aware_facade(
                container=self._container,
                enable_context_retriever=self._enable_stage_aware,
            )
            self._initialized = False
            self._facade_user_id = user_id
            self._facade_task_type = task_type

        if not self._facade:
            raise RuntimeError("StageAwareFacade 创建失败")

        if not self._initialized:
            await self._facade.initialize(
                user_id=user_id,
                task_type=task_type,
                task_complexity=task_complexity,
            )
            self._initialized = True

    def _increment_turn_counter(self) -> int:
        """递增 turn_counter 并返回新值"""
        self._turn_counter += 1
        logger.info(f"🔄 [StageAwareAdapter] Turn counter 递增到: {self._turn_counter}")
        return self._turn_counter

    def _update_shared_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """更新共享上下文，合并新的上下文信息"""
        # 更新共享上下文
        self._shared_context.update(context)
        
        # 构建增强的上下文，包含 TT 信息
        enriched_context = {
            **self._shared_context,
            "tt": {
                "turn_counter": self._turn_counter,
                "shared_context": self._shared_context,
                "adapter_instance": id(self),  # 用于调试
            }
        }
        
        logger.info(f"📝 [StageAwareAdapter] 更新共享上下文，Turn: {self._turn_counter}")
        return enriched_context

    async def generate_sql(
        self,
        *,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        complexity: "TaskComplexity" = None,
    ) -> Dict[str, Any]:
        """调用 StageAware SQL 阶段，返回结构化结果。"""
        # 动态导入以避免循环依赖
        from app.services.infrastructure.agents import TaskComplexity
        
        if complexity is None:
            complexity = TaskComplexity.MEDIUM
            
        # 递增 turn counter
        self._increment_turn_counter()
        
        await self.initialize(
            user_id=user_id,
            task_type="sql_generation",
            task_complexity=complexity,
        )

        assert self._facade, "StageAwareFacade 未初始化"

        # 更新共享上下文
        enriched_context = self._update_shared_context(context or {})

        stage_iter = self._facade.execute_sql_generation_stage(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            context=enriched_context,
        )

        result = await self._collect_stage(stage_iter)
        if result["success"]:
            sql_text = result.get("result")
            if isinstance(sql_text, str):
                result["sql"] = sql_text.strip()
            else:
                result["sql"] = sql_text
        return result

    async def generate_chart(
        self,
        *,
        chart_placeholder: str,
        etl_data: Dict[str, Any],
        user_id: str,
        task_context: Optional[Dict[str, Any]] = None,
        complexity: "TaskComplexity" = None,
    ) -> Dict[str, Any]:
        """调用 StageAware 图表阶段。"""
        # 动态导入以避免循环依赖
        from app.services.infrastructure.agents import TaskComplexity
        
        if complexity is None:
            complexity = TaskComplexity.MEDIUM
            
        # 递增 turn counter
        self._increment_turn_counter()
        
        await self.initialize(
            user_id=user_id,
            task_type="chart_generation",
            task_complexity=complexity,
        )

        assert self._facade, "StageAwareFacade 未初始化"

        # 更新共享上下文
        enriched_context = self._update_shared_context(task_context or {})

        stage_iter = self._facade.execute_chart_generation_stage(
            etl_data=etl_data,
            chart_placeholder=chart_placeholder,
            user_id=user_id,
            task_context=enriched_context,
        )

        result = await self._collect_stage(stage_iter)
        if not result["success"]:
            return result

        parsed_payload = self._parse_result_payload(result.get("result"))
        metadata = result.get("metadata") or {}

        chart_payload: Dict[str, Any] = {}
        if isinstance(parsed_payload, dict):
            chart_payload.update(
                {
                    "chart_config": parsed_payload.get("chart_config")
                    or parsed_payload.get("config"),
                    "chart_path": parsed_payload.get("chart_path"),
                    "analysis": parsed_payload.get("analysis")
                    or parsed_payload.get("insights"),
                    "recommendations": parsed_payload.get("recommendations"),
                }
            )

        if isinstance(metadata, dict):
            chart_payload.setdefault("chart_config", metadata.get("chart_config"))
            chart_payload.setdefault("chart_path", metadata.get("chart_path"))
            chart_payload.setdefault(
                "analysis", metadata.get("analysis") or metadata.get("insights")
            )

        result.update(
            {
                "chart_config": chart_payload.get("chart_config"),
                "chart_path": chart_payload.get("chart_path"),
                "analysis": chart_payload.get("analysis"),
                "recommendations": chart_payload.get("recommendations"),
            }
        )
        return result

    async def generate_document(
        self,
        *,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        task_context: Optional[Dict[str, Any]] = None,
        complexity: "TaskComplexity" = None,
    ) -> Dict[str, Any]:
        """调用 StageAware 文档阶段。"""
        # 动态导入以避免循环依赖
        from app.services.infrastructure.agents import TaskComplexity
        
        if complexity is None:
            complexity = TaskComplexity.MEDIUM
            
        # 递增 turn counter
        self._increment_turn_counter()
        
        await self.initialize(
            user_id=user_id,
            task_type="completion",
            task_complexity=complexity,
        )

        assert self._facade, "StageAwareFacade 未初始化"

        # 更新共享上下文
        enriched_context = self._update_shared_context(task_context or {})

        stage_iter = self._facade.execute_document_generation_stage(
            paragraph_context=paragraph_context,
            placeholder_data=placeholder_data,
            user_id=user_id,
            task_context=enriched_context,
        )

        result = await self._collect_stage(stage_iter)

        if result["success"]:
            parsed_payload = self._parse_result_payload(result.get("result"))
            if isinstance(parsed_payload, dict):
                result.setdefault("document_text", parsed_payload.get("document_text"))
                result.setdefault("summary", parsed_payload.get("summary"))

            if isinstance(result.get("result"), str):
                result.setdefault("document_text", result["result"])

        return result

    async def _collect_stage(self, stage_iter) -> Dict[str, Any]:
        """消费 StageAware 阶段事件，提取最终结果。"""
        # 动态导入以避免循环依赖
        from app.services.infrastructure.agents import AgentResponse
        
        final_event = None

        async for event in stage_iter:
            if event.event_type == "execution_failed":
                error_msg = ""
                if isinstance(event.data, dict):
                    error_msg = event.data.get("error", "")
                return {
                    "success": False,
                    "error": error_msg or "Stage execution failed",
                    "event_type": event.event_type,
                }

            if event.event_type == "execution_completed":
                final_event = event

        if final_event is None:
            return {
                "success": False,
                "error": "Stage completed without result",
                "event_type": "missing_execution_completed",
            }

        data = final_event.data or {}
        response = data.get("response")

        payload: Dict[str, Any] = {
            "success": True,
            "execution_time_ms": data.get("execution_time_ms"),
            "iterations": data.get("iterations_used"),
        }

        if isinstance(response, AgentResponse):
            payload.update(
                {
                    "result": response.result,
                    "result_text": self._stringify_response_result(response.result),
                    "metadata": response.metadata,
                    "quality_score": response.quality_score,
                    "reasoning": response.reasoning,
                    "tool_calls": [asdict(tc) for tc in response.tool_calls],
                    "response": asdict(response),
                }
            )
        elif is_dataclass(response):
            payload["response"] = asdict(response)
            payload["result"] = payload["response"].get("result")
        else:
            payload["response"] = response
            payload["result"] = response
            payload["result_text"] = self._stringify_response_result(response)

        return payload

    @staticmethod
    def _stringify_response_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)

    @staticmethod
    def _parse_result_payload(result: Any) -> Optional[Dict[str, Any]]:
        """
        将 LLM 返回的结果解析为 dict。
        支持 JSON 字符串或 `````json 代码块。
        """
        if isinstance(result, dict):
            return result

        if not isinstance(result, str):
            return None

        text = result.strip()

        if text.startswith("```"):
            # 去掉代码块包裹
            parts = text.split("\n", 1)
            if len(parts) == 2:
                text = parts[1]
            if text.endswith("```"):
                text = text[: -3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
