"""
AI Agent System for AutoReport

This module provides an extensible agent-based architecture for processing
intelligent placeholders, replacing the legacy intelligent_placeholder system.

Key Features:
- Modular agent-based design
- Pluggable agent types
- Unified processing pipeline
- Enhanced error handling and recovery
- Performance monitoring and metrics

Architecture:
- Base Layer: Core abstractions and interfaces
- Core Layer: Unified AI services, response parsing, error handling
- Specialized Layer: Domain-specific agents
- Enhanced Layer: Advanced features and ML capabilities
- Orchestration Layer: Agent coordination and pipeline management
"""

__version__ = "2.0.0"

# 基础层 - 核心抽象和接口（从 core_types.py 导入）
from .core_types import BaseAgent, AgentResult, AgentConfig, AgentError, AgentType, AgentStatus
from .base.base_analysis_agent import BaseAnalysisAgent

# 核心层 - 统一服务
from .core import (
    get_ai_service,
    get_analysis_parser,
    get_error_handler
)

# 专业层 - 领域特定Agent
from .specialized import (
    SchemaAnalysisAgent,
    DataAnalysisAgent,
    DataQueryAgent,
    ContentGenerationAgent,
    VisualizationAgent
)

# 编排层 - Agent协调
from .orchestration import AgentOrchestrator

# 工具层 - 通用工具
from .tools import BaseTool, tool_registry, ToolCategory

__all__ = [
    # 基础层
    "BaseAgent",
    "AgentResult", 
    "AgentConfig",
    "AgentError",
    "AgentType",
    "AgentStatus",
    "BaseAnalysisAgent",
    
    # 核心层
    "get_ai_service",
    "get_analysis_parser", 
    "get_error_handler",
    
    # 专业层
    "SchemaAnalysisAgent",
    "DataAnalysisAgent",
    "ContentGenerationAgent",
    "VisualizationAgent",
    "DataQueryAgent",
    
    # 编排层
    "AgentOrchestrator",
    
    # 工具层
    "BaseTool",
    "tool_registry",
    "ToolCategory",
]