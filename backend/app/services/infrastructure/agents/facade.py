"""
Facade providing a minimal compatibility layer on top of the Loom agent
runtime.  It mirrors the role previously played by
`app.services.infrastructure.agents.facade.AgentFacade`, but delegates all
reasoning/execution to Loom.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, Optional, Union

from loom.interfaces.llm import BaseLLM

from .types import AgentInput, AgentOutput, AgentRequest, AgentResponse
from .auth_context import auth_manager, UserAuthContext
from .config_context import config_manager, AgentSystemConfig
from .compat import agent_input_to_request, agent_response_to_output
from .config import LoomAgentConfig, ToolFactory
from .runtime import LoomAgentRuntime, build_default_runtime
from .prompts import build_system_instructions

logger = logging.getLogger(__name__)


class LoomAgentFacade:
    """
    Entry point for executing agent tasks via Loom.  Consumers only need to
    supply a service container plus an `AgentRequest` payload.
    """

    def __init__(
        self,
        *,
        container: Any,
        runtime: Optional[LoomAgentRuntime] = None,
        config: Optional[LoomAgentConfig] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        additional_tools: Optional[Iterable[ToolFactory]] = None,
        llm: Optional[BaseLLM] = None,
        include_legacy_tools: bool = True,
    ) -> None:
        self._container = container
        self._config_overrides = config_overrides or {}

        if runtime is not None:
            self._runtime = runtime
        else:
            overrides = dict(self._config_overrides)
            if config is not None:
                overrides.setdefault("llm", {})
                overrides["llm"].update(
                    {
                        "provider": config.llm.provider,
                        "model": config.llm.model,
                        "api_key": config.llm.api_key,
                        "base_url": config.llm.base_url,
                        "temperature": config.llm.temperature,
                        "max_tokens": config.llm.max_tokens,
                        "mock_responses": config.llm.mock_responses,
                        "extra_params": config.llm.extra_params,
                    }
                )
                overrides.setdefault("runtime", {})
                overrides["runtime"].update(
                    {
                        "max_iterations": config.runtime.max_iterations,
                        "max_context_tokens": config.runtime.max_context_tokens,
                        "system_prompt": config.runtime.system_prompt,
                        "enable_metrics": config.runtime.enable_metrics,
                    }
                )

            self._runtime = build_default_runtime(
                container=container,
                overrides=overrides,
                additional_tools=additional_tools,
                llm=llm,
                include_legacy_tools=include_legacy_tools,
            )

    @property
    def runtime(self) -> LoomAgentRuntime:
        return self._runtime

    def configure_auth(
        self,
        auth_context: Optional[UserAuthContext] = None,
        auth_provider: Optional[Any] = None,
    ) -> None:
        """Align with legacy facade: allow pre-setting auth context or provider."""

        if auth_context:
            auth_manager.set_context(auth_context)
        if auth_provider:
            # 兼容旧接口：暂存回调交由上层自行调用
            try:
                user_id = auth_manager.get_current_user_id()
                if user_id and callable(auth_provider):
                    ctx = auth_provider(user_id)
                    if ctx:
                        auth_manager.set_context(ctx)
            except Exception:
                pass

    def configure_system(
        self,
        config: Optional[AgentSystemConfig] = None,
        config_loader: Optional[Any] = None,
    ) -> None:
        if config:
            config_manager.set_config(config)
        if config_loader:
            config_manager.set_config_loader(config_loader)

    def _parse_llm_output(self, raw_output: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse the raw LLM response into structured content.

        Expected JSON schema:
            {
                "sql": "SELECT ...",
                "analysis": {...},
                "test_result": {...},
                "warnings": [...],
                "fallback_reason": "..."
            }
        """

        metadata_updates: Dict[str, Any] = {}

        try:
            parsed = json.loads(raw_output)
            if not isinstance(parsed, dict):
                raise ValueError('LLM output is not a JSON object')

            sql = parsed.get('sql') or parsed.get('result') or parsed.get('content')
            if isinstance(sql, dict):
                sql = sql.get('text') or sql.get('value')
            if not isinstance(sql, str) or not sql.strip():
                sql = raw_output

            for key in ('analysis', 'test_result', 'warnings', 'observations', 'metadata'):
                if key in parsed and parsed[key]:
                    metadata_updates[key] = parsed[key]

            return sql, metadata_updates
        except Exception:
            logger.warning('⚠️ LLM output JSON parsing failed; using raw output.')
            metadata_updates['parsing_error'] = True
            return raw_output, metadata_updates

    def _compose_prompt(self, request: AgentRequest) -> str:
        """Convert the structured request into a single prompt string."""

        context_json = ""
        if request.context:
            try:
                context_json = json.dumps(request.context, ensure_ascii=False, indent=2)
            except TypeError:
                context_json = json.dumps(
                    {k: str(v) for k, v in request.context.items()},
                    ensure_ascii=False,
                    indent=2,
                )

        tool_section = ""
        available_tools = request.context.get("available_tools", [])
        if available_tools:
            lines = [f"- {tool['name']}: {tool.get('desc', '')}" for tool in available_tools]
            tool_section = "\n".join(lines)

        sections = [
            "你是AutoReport的智能分析助手，需要根据输入信息完成任务。",
            f"### 执行阶段\n{request.stage}",
            f"### 工作模式\n{request.mode}",
            f"### 用户需求\n{request.prompt}",
        ]
        if tool_section:
            sections.append(f"### 可用工具\n{tool_section}")
        if context_json:
            sections.append(f"### 上下文信息\n{context_json}")
        return "\n\n".join(sections)

    async def execute(self, request: Union[AgentRequest, AgentInput]) -> AgentResponse:
        """
        Execute a user request through Loom.  The context metadata is encoded
        into the prompt to preserve behaviour parity with the legacy system's
        prompt builder.
        """

        request_obj = request if isinstance(request, AgentRequest) else agent_input_to_request(request)

        available_tools = request_obj.context.get("available_tools", [])
        system_prompt = build_system_instructions(request_obj.stage, available_tools)
        self._runtime.agent.executor.system_instructions = system_prompt

        prompt = self._compose_prompt(request_obj)
        logger.info("Executing Loom agent task user_id=%s", request_obj.user_id)

        try:
            raw_output = await self._runtime.run(
                prompt,
                user_id=request_obj.user_id,
                stage=request_obj.stage,
                output_kind=request_obj.metadata.get("output_kind") if request_obj.metadata else None,
            )

            parsed_output, metadata_updates = self._parse_llm_output(raw_output)

            metadata = {
                "prompt": prompt,
                "tools": [tool.name for tool in self._runtime.tools],
            }
            metadata.update(request_obj.metadata)
            metadata.update(metadata_updates)

            return AgentResponse(success=True, output=parsed_output, metadata=metadata)
        except Exception as exc:
            logger.exception("Loom agent execution failed: %s", exc)
            metadata = {
                "prompt": prompt,
                "tools": [tool.name for tool in self._runtime.tools],
            }
            metadata.update(request_obj.metadata)
            return AgentResponse(success=False, output="", error=str(exc), metadata=metadata)

    async def execute_legacy(self, agent_input: AgentInput) -> AgentOutput:
        """
        Convenience wrapper that accepts a legacy `AgentInput` and returns an
        `AgentOutput`, enabling drop-in replacement in existing services.
        """

        response = await self.execute(agent_input)
        return agent_response_to_output(response)

    async def execute_task_validation(self, agent_input: AgentInput) -> AgentOutput:
        """Compatibility helper replicating旧系统的任务验证流程入口。"""

        request = agent_input_to_request(agent_input)
        request.stage = "task_execution"
        request.mode = "task_execution"
        request.metadata["task_mode"] = "validation"

        response = await self.execute(request)
        if response.success:
            return agent_response_to_output(response)

        # 如果验证失败且不存在历史SQL，则回退到模板模式重新生成
        has_sql = False
        tdc = request.context.get("task_driven_context", {})
        if isinstance(tdc, dict):
            sql_val = tdc.get("current_sql") or tdc.get("existing_sql")
            has_sql = bool(sql_val)

        if not has_sql:
            request.stage = "template"
            request.mode = "template"
            request.metadata["task_mode"] = "regenerate"
            response = await self.execute(request)

        return agent_response_to_output(response)


class AgentFacade(LoomAgentFacade):
    """向后兼容别名，允许旧代码继续导入 AgentFacade。"""


__all__ = [
    "LoomAgentFacade",
    "AgentFacade",
]
