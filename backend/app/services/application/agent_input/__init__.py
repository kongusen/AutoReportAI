"""
Agent Input package

集中与 AgentInput 构建、执行相关的应用层能力：
- builder: 负责 Context -> AgentInput 的映射与动态prompt组装
- bridge: 负责一键式 构建 -> 执行 PTOF
"""

from .builder import AgentInputBuilder
from .bridge import AgentInputBridge

__all__ = [
    "AgentInputBuilder",
    "AgentInputBridge",
]

