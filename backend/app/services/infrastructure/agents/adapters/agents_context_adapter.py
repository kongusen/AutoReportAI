"""
Agents Context Adapter (Infrastructure)

Converts Domain structured contexts to the existing agents' AgentInput types.
This adapter intentionally stays technical: it builds prompts (via prompt
templates/controllers) and fills AgentInput without embedding business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.services.infrastructure.agents.types import (
    AgentInput, PlaceholderSpec as AgentPlaceholderSpec, SchemaInfo as AgentSchemaInfo,
    TaskContext as AgentTaskContext, AgentConstraints,
)


@dataclass
class PlaceholderContext:
    name: str
    text: str
    kind: str  # period | statistical | chart


class AgentsContextAdapter:
    """Adapter to map Domain context to AgentInput."""

    def __init__(self, prompt_builder: callable) -> None:
        self._prompt_builder = prompt_builder

    def to_agent_input(
        self,
        placeholder: PlaceholderContext,
        domain_ctx: Dict[str, Any],  # expects keys: template, schema, task, stage
        time_window: Dict[str, Any],
    ) -> AgentInput:
        # Build placeholder spec
        ph_spec = AgentPlaceholderSpec(
            id=placeholder.name,
            description=placeholder.text,
            type="chart" if placeholder.kind == "chart" else "stat",
            granularity=time_window.get("granularity", "daily"),
        )

        # Map schema (technical view only)
        schema_info = AgentSchemaInfo(
            tables=domain_ctx["schema"].get("tables", []),
            columns=domain_ctx["schema"].get("columns", {}),
        )

        # Map task context (technical view only)
        task_ctx = AgentTaskContext(
            task_time=domain_ctx["task"]["execution_time"],
            timezone=domain_ctx["task"].get("timezone", "Asia/Shanghai"),
            window=time_window,
        )

        constraints = AgentConstraints(
            sql_only=(placeholder.kind != "chart"),
            output_kind="chart" if placeholder.kind == "chart" else "sql",
            max_attempts=3,
        )

        # Build technical prompt
        user_prompt = self._prompt_builder(placeholder, domain_ctx)

        return AgentInput(
            user_prompt=user_prompt,
            placeholder=ph_spec,
            schema=schema_info,
            context=task_ctx,
            constraints=constraints,
            template_id=domain_ctx["template"]["template_id"],
            data_source={"data_source_id": domain_ctx["schema"].get("data_source_id")},
        )

