from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from ..core.context_manager import get_context_manager, ContextScope
from .engine import OrchestrationEngine
from .plan_generator import PlanGenerator
from ..context.execution_context import EnhancedExecutionContext


class UnifiedQueryController:
    def __init__(self):
        self.engine = OrchestrationEngine()
        self.plan_generator = PlanGenerator()

    async def process_request(self, *, session_id: str, placeholder_id: str, user_id: str,
                              statistics_period: str | None = None,
                              task_time: datetime | None = None) -> Dict[str, Any]:
        cm = get_context_manager()
        cm.set_task_time_constraints(
            session_id,
            statistics_period=statistics_period,
            task_time=task_time,
            scope=ContextScope.TASK,
        )

        exec_ctx = EnhancedExecutionContext(session_id=session_id,
                                             user_id=user_id,
                                             request={'placeholder_id': placeholder_id})
        exec_ctx.time_constraints = cm.get_task_time_constraints(session_id)

        plan = self.plan_generator.generate_plan(placeholder_id=placeholder_id, context=exec_ctx)
        result = await self.engine.execute_plan(plan, exec_ctx)
        return result


