"""
Agent Tools System
==================

简化的工具系统，包含核心工具和基础框架。
"""

# 核心工具框架
from .core.base import (
    AgentTool,
    StreamingAgentTool, 
    ToolDefinition,
    ToolResult,
    ToolExecutionContext,
    ToolCategory,
    ToolPriority,
    ToolPermission,
    ValidationError,
    ExecutionError,
    create_tool_definition
)

# 尝试导入现有的数据工具
try:
    from .data.sql_tool import SQLGeneratorTool, SQLExecutorTool
except ImportError:
    SQLGeneratorTool = None
    SQLExecutorTool = None

try:
    from .data.analysis_tool import DataAnalysisTool
except ImportError:
    DataAnalysisTool = None

try:
    from .data.report_tool import ReportGeneratorTool
except ImportError:
    ReportGeneratorTool = None

# 尝试导入AI工具
try:
    from .ai.reasoning_tool import ReasoningTool
except ImportError:
    ReasoningTool = None

# 尝试导入LLM工具
try:
    from .llm.llm_execution_tool import LLMExecutionTool
    from .llm.llm_reasoning_tool import LLMReasoningTool
    from .llm import LLMTaskType, ReasoningDepth
except ImportError:
    LLMExecutionTool = None
    LLMReasoningTool = None
    LLMTaskType = None
    ReasoningDepth = None

# 尝试导入系统工具
try:
    from .system.bash_tool import BashTool
except ImportError:
    BashTool = None

try:
    from .system.file_tool import FileTool
except ImportError:
    FileTool = None

try:
    from .system.search_tool import SearchTool
except ImportError:
    SearchTool = None

# 从注册表导入核心功能
from .core.registry import get_tool_registry, ToolRegistry, register_tool, get_available_tools, discover_tools

# 构建导出列表，只包含存在的组件
__all__ = [
    # 核心框架 - 这些始终存在
    "AgentTool",
    "StreamingAgentTool",
    "ToolDefinition", 
    "ToolResult",
    "ToolExecutionContext",
    "ToolCategory",
    "ToolPriority",
    "ToolPermission",
    "ValidationError",
    "ExecutionError",
    "create_tool_definition",
    # 注册表功能
    "get_tool_registry",
    "ToolRegistry", 
    "register_tool",
    "get_available_tools",
    "discover_tools"
]

# 只导出存在的工具
if SQLGeneratorTool is not None:
    __all__.append("SQLGeneratorTool")
if SQLExecutorTool is not None:
    __all__.append("SQLExecutorTool")
if DataAnalysisTool is not None:
    __all__.append("DataAnalysisTool")
if ReportGeneratorTool is not None:
    __all__.append("ReportGeneratorTool")
if ReasoningTool is not None:
    __all__.append("ReasoningTool")
if LLMExecutionTool is not None:
    __all__.append("LLMExecutionTool")
if LLMReasoningTool is not None:
    __all__.append("LLMReasoningTool")
if LLMTaskType is not None:
    __all__.append("LLMTaskType")
if ReasoningDepth is not None:
    __all__.append("ReasoningDepth")
if BashTool is not None:
    __all__.append("BashTool")
if FileTool is not None:
    __all__.append("FileTool")
if SearchTool is not None:
    __all__.append("SearchTool")