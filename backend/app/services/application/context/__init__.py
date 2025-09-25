"""
Application层上下文构建模块
提供各种上下文构建器，将业务需求转换为Domain层可用的上下文对象

核心三大构建器（来自backup2）：
- DataSourceContextBuilder: 数据源上下文构建，支持Agent智能分析
- TemplateContextBuilder: 模板上下文构建，专注于占位符语境匹配
- TaskDrivenContextBuilder: 任务驱动上下文构建，为Agent React迭代设计

原有构建器：
- TimeContextBuilder: 时间上下文构建
- BusinessContextBuilder: 业务上下文构建
- DocumentContextBuilder: 文档上下文构建
"""

# 核心三大构建器
from .data_source_context_server import DataSourceContextBuilder
from .template_context_service import TemplateContextBuilder
from .task_context_service import TaskDrivenContextBuilder

# 统一上下文协调器
from .context_coordinator import ContextCoordinator, Context

__all__ = [
    # 核心三大构建器
    'DataSourceContextBuilder',
    'TemplateContextBuilder',
    'TaskDrivenContextBuilder',

    # 统一协调器
    'ContextCoordinator',
    'Context'
]