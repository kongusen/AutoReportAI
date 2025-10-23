"""
Loom-based agent runtime entry points.

This lightweight package hosts the experimental implementation of the
AutoReport AI agent system powered by the `loom` framework.  It will
eventually replace `app/services/infrastructure/agents` once the new
runtime is battle-tested.
"""

from .config import LoomAgentConfig, LLMRuntimeConfig, RuntimeOptions, resolve_runtime_config
from .runtime import LoomAgentRuntime, build_default_runtime
from .facade import LoomAgentFacade, AgentFacade
from .types import (
    AgentRequest,
    AgentResponse,
    AgentInput,
    AgentOutput,
    PlaceholderSpec,
    SchemaInfo,
    TaskContext,
    AgentConstraints,
)
from .compat import agent_input_to_request, agent_response_to_output
from .service import LoomAgentService, AgentService
from .data_source_security_service import data_source_security_service, DataSourceSecurityService
from .orchestrator import (
    ReportGenerationOrchestrator,
    OrchestratorContext,
    StageStatus,
    StageResult,
)

__all__ = [
    "LoomAgentConfig",
    "LLMRuntimeConfig",
    "RuntimeOptions",
    "resolve_runtime_config",
    "LoomAgentRuntime",
    "build_default_runtime",
    "LoomAgentFacade",
    "AgentFacade",
    "AgentInput",
    "AgentOutput",
    "PlaceholderSpec",
    "SchemaInfo",
    "TaskContext",
    "AgentConstraints",
    "AgentRequest",
    "AgentResponse",
    "agent_input_to_request",
    "agent_response_to_output",
    "LoomAgentService",
    "AgentService",
    "data_source_security_service",
    "DataSourceSecurityService",
    "ReportGenerationOrchestrator",
    "OrchestratorContext",
    "StageStatus",
    "StageResult",
]
