"""
AutoReportAI Agent 核心模块
借鉴 Claude Code 的系统性代理思想
"""

from .messages import AgentMessage, MessageType, ProgressData, ErrorData
from .tasks import AgentTask, TaskType
from .controller import AgentController
from .context import ContextManager, TaskContext, TemplateContext, DataSourceContext, ExecutionContext

__all__ = [
    "AgentMessage",
    "MessageType", 
    "ProgressData",
    "ErrorData",
    "AgentTask",
    "TaskType",
    "AgentController",
    "ContextManager",
    "TaskContext",
    "TemplateContext", 
    "DataSourceContext",
    "ExecutionContext"
]