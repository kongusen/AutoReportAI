"""
Task Execution Components

任务执行组件，包括：
- 智能报告生成流水线
- Agent执行器
- 回退处理机制
"""

from .pipeline import (
    intelligent_report_generation_pipeline,
    enhanced_intelligent_report_generation_pipeline
)
from .agent_executor import AgentExecutor
from .fallback import FallbackHandler

__all__ = [
    "intelligent_report_generation_pipeline",
    "enhanced_intelligent_report_generation_pipeline",
    "AgentExecutor",
    "FallbackHandler",
]
