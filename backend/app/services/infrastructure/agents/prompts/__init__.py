"""
Prompt 模块 - 统一的提示词管理

提供：
- SystemPromptBuilder: 系统级提示词构建
- StagePromptManager: 阶段级提示词管理
- PromptTemplate: 模板化提示词生成
- PromptTemplateManager: 模板管理器
- ContextFormatter: 上下文格式化工具
"""

# 系统提示构建器
from .system import SystemPromptBuilder

# 阶段提示管理器
from .stages import StagePromptManager

# 模板和格式化
from .templates import (
    PromptTemplate,
    PromptTemplateManager,
    ContextFormatter
)

__all__ = [
    # System
    "SystemPromptBuilder",

    # Stages
    "StagePromptManager",

    # Templates
    "PromptTemplate",
    "PromptTemplateManager",
    "ContextFormatter",
]
