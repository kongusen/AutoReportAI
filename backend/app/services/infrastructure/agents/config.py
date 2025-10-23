"""
Configuration helpers for the Loom-backed agent runtime.

The configuration is intentionally lightweight so that it can be easily
constructed in tests or composed with existing dependency injection
infrastructure.  The intent is to mirror the core knobs we expect the
future production runtime to expose while keeping sensible defaults for
local development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, is_dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from loom.interfaces.tool import BaseTool

# Tool factories receive the service container (if needed) and should return
# an instantiated loom BaseTool.  The callable is typed loosely on purpose so
# factories that do not need the container can ignore the argument.
ToolFactory = Callable[..., BaseTool]


@dataclass
class LLMRuntimeConfig:
    """
    Parameters required to construct the low-level LLM client that powers the
    Loom agent.  Values default to a `mock` provider so unit tests can run
    without external services.
    """

    provider: str = field(
        default_factory=lambda: os.getenv("LOOM_PROVIDER", "mock")
    )
    model: str = field(
        default_factory=lambda: os.getenv("LOOM_MODEL", "mock-llm")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("LOOM_API_KEY")
    )
    base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("LOOM_BASE_URL")
    )
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    mock_responses: Sequence[str] | None = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeOptions:
    """
    Loom agent tuning parameters.  These settings map directly to the keyword
    arguments accepted by `loom.agent`.
    """

    max_iterations: int = 20
    max_context_tokens: int = 16000
    system_prompt: Optional[str] = None
    tool_factories: Sequence[ToolFactory] = field(default_factory=tuple)
    callbacks: Sequence[Any] = field(default_factory=tuple)
    enable_metrics: bool = False


@dataclass
class LoomAgentConfig:
    """Top-level configuration container."""

    llm: LLMRuntimeConfig = field(default_factory=LLMRuntimeConfig)
    runtime: RuntimeOptions = field(default_factory=RuntimeOptions)


def resolve_runtime_config(
    overrides: Mapping[str, Any] | None = None,
) -> LoomAgentConfig:
    """
    Produce a fully-populated configuration object, optionally applying a set
    of overrides.  The implementation performs a shallow recursive update so
    nested dataclasses can be customised without reconstructing the entire
    object graph.
    """

    config = LoomAgentConfig()
    if overrides:
        _apply_overrides(config, dict(overrides))
    return config


def _apply_overrides(target: Any, updates: Dict[str, Any]) -> None:
    for key, value in updates.items():
        if not hasattr(target, key):
            continue
        current = getattr(target, key)
        if is_dataclass(current) and isinstance(value, Mapping):
            _apply_overrides(current, dict(value))
        else:
            setattr(target, key, value)


__all__ = [
    "LoomAgentConfig",
    "LLMRuntimeConfig",
    "RuntimeOptions",
    "ToolFactory",
    "resolve_runtime_config",
]
