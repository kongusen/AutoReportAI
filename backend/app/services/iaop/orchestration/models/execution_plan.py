from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .task_node import TaskNode


@dataclass
class ExecutionPlan:
    steps: List[TaskNode]

    def get_execution_order(self) -> List[TaskNode]:
        return self.steps


