"""
Convenience service wiring the Loom agent facade into the existing backend
container.  This mirrors the public surface of the legacy AgentFacade so that
callers can switch implementations with minimal changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from .types import AgentInput, AgentOutput
from .config import LoomAgentConfig, ToolFactory
from .facade import LoomAgentFacade


class LoomAgentService:
    def __init__(
        self,
        *,
        container: Any,
        config: Optional[LoomAgentConfig] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        additional_tools: Optional[Iterable[ToolFactory]] = None,
    ) -> None:
        self._facade = LoomAgentFacade(
            container=container,
            config=config,
            config_overrides=config_overrides,
            additional_tools=additional_tools,
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def facade(self) -> LoomAgentFacade:
        return self._facade

    def configure_auth(self, *args, **kwargs) -> None:
        self._facade.configure_auth(*args, **kwargs)

    def configure_system(self, *args, **kwargs) -> None:
        self._facade.configure_system(*args, **kwargs)

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        result = await self._facade.execute_legacy(agent_input)
        if not self._looks_like_sql(result.result):
            self._logger.warning(
                "⚠️ [LoomAgentService] Loom execution produced non-SQL output (preview=%s).",
                str(result.result)[:80],
            )
        return result

    async def execute_task_validation(self, agent_input: AgentInput) -> AgentOutput:
        result = await self._facade.execute_task_validation(agent_input)
        if not self._looks_like_sql(result.result):
            self._logger.warning(
                "⚠️ [LoomAgentService] Loom validation produced non-SQL output (preview=%s).",
                str(result.result)[:80],
            )
        return result

    @staticmethod
    def _looks_like_sql(value: Any) -> bool:
        if isinstance(value, dict):
            value = value.get("sql") or next(iter(value.values()), "")
        if not isinstance(value, str):
            return False
        sql = value.strip().upper()
        return sql.startswith(("SELECT", "WITH"))


class AgentService(LoomAgentService):
    """向后兼容别名。"""


__all__ = ["LoomAgentService", "AgentService"]
