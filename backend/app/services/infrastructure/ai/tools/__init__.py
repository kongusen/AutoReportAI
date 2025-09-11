"""
新一代AI工具系统 v2.0
===============================================

基于优化提示词系统重新构建的工具架构：
- 与最新的prompts.py完全集成
- 强制约束和安全防护机制
- 迭代学习和错误纠正能力
- 结构化输出和验证系统
- ReAct orchestrator 工具名称桥接
"""

from ..core.tools import BaseTool, IterativeTool, ToolContext, ToolResult, ToolResultType, ToolChain
from .sql_generator import AdvancedSQLGenerator
from .data_analyzer import SmartDataAnalyzer  
from .report_generator import IntelligentReportGenerator
from .orchestrator import PromptAwareOrchestrator
from .bridge_tools import (
    TemplateInfoTool, 
    DataAnalyzerTool, 
    SqlGeneratorTool,
    DataSourceInfoTool,
    register_bridge_tools
)

__all__ = [
    "BaseTool",
    "IterativeTool",
    "ToolContext", 
    "ToolResult",
    "ToolResultType",
    "ToolChain",
    "AdvancedSQLGenerator",
    "SmartDataAnalyzer",
    "IntelligentReportGenerator", 
    "PromptAwareOrchestrator",
    "TemplateInfoTool",
    "DataAnalyzerTool",
    "SqlGeneratorTool", 
    "DataSourceInfoTool",
    "register_bridge_tools"
]

__version__ = "2.1.0"
__description__ = "新一代AI工具系统，基于优化提示词架构，包含ReAct桥接工具"