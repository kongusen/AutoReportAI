"""
Agent工具模块

提供Agent系统使用的各种工具，包括：
- 数据处理工具
- 分析工具 
- 可视化工具
- 内容生成工具
- 安全工具
- 优化工具
"""

from .base_tool import (
    BaseTool, 
    ToolMetadata, 
    ToolCategory, 
    ToolPriority,
    ToolConfig, 
    ToolResult, 
    ToolDependency,
    ToolRegistry,
    tool_registry
)

from .data_processing_tools import (
    DataValidationTool,
    DataTransformTool,
    DataCleaningTool,
    SchemaDetectionTool
)

# 注册数据处理工具
tool_registry.register_tool(DataValidationTool, DataValidationTool.default_metadata())
tool_registry.register_tool(DataTransformTool, DataTransformTool.default_metadata())
tool_registry.register_tool(DataCleaningTool, DataCleaningTool.default_metadata())
tool_registry.register_tool(SchemaDetectionTool, SchemaDetectionTool.default_metadata())

__all__ = [
    # 基础工具框架
    'BaseTool',
    'ToolMetadata', 
    'ToolCategory',
    'ToolPriority',
    'ToolConfig',
    'ToolResult',
    'ToolDependency',
    'ToolRegistry',
    'tool_registry',
    
    # 数据处理工具
    'DataValidationTool',
    'DataTransformTool', 
    'DataCleaningTool',
    'SchemaDetectionTool'
]