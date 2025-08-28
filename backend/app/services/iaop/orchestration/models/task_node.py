from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from ...context.execution_context import EnhancedExecutionContext


class AsyncExecutor(Protocol):
    def __call__(self, context: EnhancedExecutionContext) -> Awaitable[dict]:
        ...


@dataclass
class TaskNode:
    task_id: str
    executor: AsyncExecutor

    async def execute(self, context: EnhancedExecutionContext) -> dict:
        return await self.executor(context)


