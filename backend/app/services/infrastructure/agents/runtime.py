"""
Runtime builder that wires configuration, tools and the Loom agent together.

The goal is to keep the entry point small but expressive so that we can swap
in different tool sets or LLM configurations without touching consumers.
"""

from __future__ import annotations

import logging
import asyncio
import contextvars
from typing import Any, Dict, Iterable, Optional, Sequence, List

from loom import Agent, agent as build_agent
from loom.builtin.llms import MockLLM
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.llm.config import LLMConfig, LLMProvider
from loom.llm.factory import LLMFactory

from .config import (
    LLMRuntimeConfig,
    LoomAgentConfig,
    RuntimeOptions,
    ToolFactory,
    resolve_runtime_config,
)
from .tools import build_default_tool_factories


class ContainerLLMAdapter(BaseLLM):
    """Bridge the existing container LLM service to Loom's BaseLLM interface."""

    def __init__(self, service: Any, logger: Optional[logging.Logger] = None, default_user_id: str = "system") -> None:
        if not hasattr(service, "ask"):
            raise ValueError("Container LLM service must expose an async 'ask' method.")
        self._service = service
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._default_user_id = default_user_id
        self._model_name = getattr(service, "default_model", "container-llm")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        prompt = self._extract_prompt(messages)
        user_id = self._extract_user_id(messages)
        try:
            response = await self._service.ask(
                user_id=user_id,
                prompt=prompt,
                response_format={"type": "json_object"},
                llm_policy={
                    "stage": _CURRENT_STAGE.get("agent_runtime"),
                    "output_kind": _CURRENT_OUTPUT_KIND.get("text"),
                },
            )
        except Exception as exc:  # pragma: no cover - container side errors
            self._logger.error("Container LLM service failed: %s", exc)
            raise

        if isinstance(response, dict):
            for key in ("response", "result", "text", "sql", "content"):
                if response.get(key):
                    self._logger.debug(
                        "🧠 [ContainerLLMAdapter] user=%s key=%s preview=%s",
                        user_id,
                        key,
                        str(response[key])[:80],
                    )
                    return response[key]
            return str(response)
        self._logger.debug(
            "🧠 [ContainerLLMAdapter] user=%s raw_response=%s", user_id, str(response)[:80]
        )
        return str(response)

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        text = await self.generate(messages)
        return {"content": text, "tool_calls": []}

    async def stream(self, messages: List[Dict]):
        text = await self.generate(messages)
        for ch in text:
            await asyncio.sleep(0)
            yield ch

    def _extract_prompt(self, messages: List[Dict]) -> str:
        user_messages = [m.get("content") for m in messages if m.get("role") == "user" and m.get("content")]
        if user_messages:
            return user_messages[-1]
        fallback = [m.get("content") for m in messages if m.get("content")]
        return fallback[-1] if fallback else ""

    def _extract_user_id(self, messages: List[Dict]) -> str:
        ctx_user = _CURRENT_USER_ID.get()
        if ctx_user:
            return ctx_user
        for m in reversed(messages):
            metadata = m.get("metadata") or {}
            if isinstance(metadata, dict) and metadata.get("user_id"):
                return metadata["user_id"]
        return self._default_user_id


class LoomAgentRuntime:
    """
    Thin wrapper around a Loom `Agent` that keeps track of the instantiated
    tools and provides convenience helpers for execution.
    """

    def __init__(
        self,
        agent: Agent,
        tools: Sequence[BaseTool],
        config: LoomAgentConfig,
    ) -> None:
        self._agent = agent
        self._tools = tuple(tools)
        self._config = config

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def config(self) -> LoomAgentConfig:
        return self._config

    @property
    def tools(self) -> Sequence[BaseTool]:
        return self._tools

    async def run(self, prompt: str, **kwargs) -> str:
        """Proxy to the underlying Loom agent."""
        user_id = kwargs.pop("user_id", None)
        stage = kwargs.pop("stage", None)
        output_kind = kwargs.pop("output_kind", None)
        tokens = []
        if user_id:
            tokens.append((_CURRENT_USER_ID, _CURRENT_USER_ID.set(user_id)))
        if stage:
            tokens.append((_CURRENT_STAGE, _CURRENT_STAGE.set(stage)))
        if output_kind:
            tokens.append((_CURRENT_OUTPUT_KIND, _CURRENT_OUTPUT_KIND.set(output_kind)))
        try:
            return await self._agent.run(prompt, **kwargs)
        finally:
            for var, token in reversed(tokens):
                var.reset(token)

    async def stream(self, prompt: str):
        async for event in self._agent.stream(prompt):
            yield event


def build_default_runtime(
    *,
    container: Any,
    overrides: Optional[Dict[str, Any]] = None,
    additional_tools: Optional[Iterable[ToolFactory]] = None,
    llm: Optional[BaseLLM] = None,
    include_legacy_tools: bool = True,
) -> LoomAgentRuntime:
    """
    Construct a runtime using the default configuration and tool set.

    Args:
        container: application service container (passed to tool factories).
        overrides: optional configuration overrides.
        additional_tools: tool factories appended to the default list.
        llm: explicitly provided LLM; if None a new one is built from config.
    """

    config = resolve_runtime_config(overrides)
    tool_factories: list[ToolFactory] = []
    if include_legacy_tools:
        tool_factories.extend(build_default_tool_factories())
    if additional_tools:
        tool_factories.extend(additional_tools)

    tools = [factory(container) for factory in tool_factories]

    if llm is None:
        container_llm = _build_container_llm_if_available(container)
        if container_llm is not None:
            llm = container_llm

    loom_agent = _create_agent(
        llm_cfg=config.llm,
        runtime_cfg=config.runtime,
        tools=tools,
        llm=llm,
    )

    return LoomAgentRuntime(agent=loom_agent, tools=tools, config=config)


def _create_agent(
    *,
    llm_cfg: LLMRuntimeConfig,
    runtime_cfg: RuntimeOptions,
    tools: Sequence[BaseTool],
    llm: Optional[BaseLLM],
) -> Agent:
    """Instantiate a Loom Agent based on the supplied config."""

    agent_kwargs: Dict[str, Any] = {
        "tools": list(tools),
        "max_iterations": runtime_cfg.max_iterations,
        "max_context_tokens": runtime_cfg.max_context_tokens,
    }

    if runtime_cfg.system_prompt:
        agent_kwargs["system_instructions"] = runtime_cfg.system_prompt
    if runtime_cfg.callbacks:
        agent_kwargs["callbacks"] = list(runtime_cfg.callbacks)

    # Support passing a pre-built LLM (useful for tests) or build one via Loom.
    if llm is not None:
        agent_kwargs["llm"] = llm
    else:
        agent_kwargs["llm"] = _build_llm(llm_cfg)

    return build_agent(**agent_kwargs)


def _build_llm(config: LLMRuntimeConfig) -> BaseLLM:
    """Translate our config to an actual Loom LLM instance."""

    provider_value = (config.provider or "mock").lower()
    if provider_value in {"mock", "test", ""}:
        responses = list(config.mock_responses or ["OK"])
        return MockLLM(responses=responses, name=config.model or "mock-llm")

    try:
        provider = LLMProvider(provider_value)
    except ValueError as exc:  # pragma: no cover - configuration error
        raise ValueError(f"Unsupported LLM provider: {config.provider}") from exc

    llm_config = _build_llm_config(provider, config)
    return LLMFactory.create(llm_config)


def _build_llm_config(provider: LLMProvider, cfg: LLMRuntimeConfig) -> LLMConfig:
    kwargs: Dict[str, Any] = {
        "temperature": cfg.temperature,
    }
    if cfg.max_tokens is not None:
        kwargs["max_tokens"] = cfg.max_tokens
    if cfg.extra_params:
        kwargs.update(cfg.extra_params)

    if provider == LLMProvider.OPENAI:
        if not cfg.api_key:
            raise ValueError("OpenAI provider requires an api_key")
        return LLMConfig.openai(
            api_key=cfg.api_key,
            model=cfg.model,
            base_url=cfg.base_url,
            **kwargs,
        )
    if provider == LLMProvider.AZURE_OPENAI:
        if not cfg.api_key or not cfg.base_url:
            raise ValueError("Azure OpenAI provider requires api_key and base_url (endpoint)")
        return LLMConfig.azure_openai(
            api_key=cfg.api_key,
            deployment_name=cfg.model,
            endpoint=cfg.base_url,
            **kwargs,
        )
    if provider == LLMProvider.ANTHROPIC:
        if not cfg.api_key:
            raise ValueError("Anthropic provider requires an api_key")
        return LLMConfig.anthropic(
            api_key=cfg.api_key,
            model=cfg.model,
            **kwargs,
        )
    if provider == LLMProvider.COHERE:
        if not cfg.api_key:
            raise ValueError("Cohere provider requires an api_key")
        return LLMConfig.cohere(
            api_key=cfg.api_key,
            model=cfg.model,
            **kwargs,
        )
    if provider == LLMProvider.GOOGLE:
        if not cfg.api_key:
            raise ValueError("Google provider requires an api_key")
        return LLMConfig.google(
            api_key=cfg.api_key,
            model=cfg.model,
            **kwargs,
        )
    if provider == LLMProvider.OLLAMA:
        if not cfg.base_url:
            raise ValueError("Ollama provider requires base_url")
        return LLMConfig.ollama(
            model=cfg.model,
            base_url=cfg.base_url,
            **kwargs,
        )
    if provider == LLMProvider.CUSTOM:
        if not cfg.base_url:
            raise ValueError("Custom provider requires base_url")
        return LLMConfig.custom(
            model_name=cfg.model,
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            **kwargs,
        )
    raise ValueError(f"Provider {provider.value} is not supported")


def _build_container_llm_if_available(container: Any) -> Optional[BaseLLM]:
    service = None
    for attr in ("llm", "llm_service"):
        if hasattr(container, attr):
            service = getattr(container, attr)
            break
    if service is None:
        return None
    try:
        adapter = ContainerLLMAdapter(service)
        logging.getLogger(__name__).info("🧠 [LoomRuntime] Using container LLM service via %s", type(service).__name__)
        return adapter
    except Exception as exc:
        logging.getLogger(__name__).warning("⚠️ [LoomRuntime] Failed to adapt container LLM service: %s", exc)
        return None


_CURRENT_USER_ID = contextvars.ContextVar("loom_agent_user_id", default="")
_CURRENT_STAGE = contextvars.ContextVar("loom_agent_stage", default="agent_runtime")
_CURRENT_OUTPUT_KIND = contextvars.ContextVar("loom_agent_output_kind", default="text")


__all__ = [
    "LoomAgentRuntime",
    "build_default_runtime",
]
