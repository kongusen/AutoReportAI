"""
Task Execution Components

任务执行组件，包括：
- 智能报告生成流水线
- Agent执行器
- 回退处理机制
"""

from .unified_pipeline import (
    unified_report_generation_pipeline,
    PipelineMode
)
# AgentExecutor not available
from .fallback import FallbackHandler

__all__ = [
    "unified_report_generation_pipeline",
    "PipelineMode",
    # "AgentExecutor",
    "FallbackHandler",
]
