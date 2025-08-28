from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from ..agents.base import BaseAgent


@dataclass
class AgentDescriptor:
    name: str
    cls: Type[BaseAgent]
    capabilities: List[str]


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDescriptor] = {}

    def register(self, descriptor: AgentDescriptor) -> None:
        self._agents[descriptor.name] = descriptor

    def get(self, name: str) -> Optional[AgentDescriptor]:
        return self._agents.get(name)

    def list(self) -> List[AgentDescriptor]:
        return list(self._agents.values())


