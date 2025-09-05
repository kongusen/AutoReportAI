"""
AutoReportAI Agent 核心智能代理服务

提供AutoReportAI系统的核心智能代理组件：

核心组件：
1. AutoReportAIAgent - 主编排器，协调三大核心功能
2. PlaceholderToSQLAgent - 占位符→SQL转换专用代理
3. TaskSupplementAgent - 任务补充机制代理
4. MultiContextIntegrator - 多上下文集成器
5. SQLTestingValidator - SQL测试验证器
6. ToolBasedAgent - 现代化工具注册架构代理

设计理念：
- 聚焦三大核心功能：占位符→SQL转换、任务补充机制、图表生成
- 支持五大主要工作流
- 基于现代化工具注册架构
- 多上下文智能集成（数据源、任务、模板、时间）
- 删除冗余组件，保持核心功能
"""

from typing import TYPE_CHECKING

# 类型检查时的延迟导入
if TYPE_CHECKING:
    from .autoreport_ai_agent import AutoReportAIAgent
    from .placeholder_to_sql_agent import PlaceholderToSqlAgent
    from .task_supplement_agent import TaskSupplementAgent
    from .multi_context_integrator import MultiContextIntegrator
    from .sql_testing_validator import SqlTestingValidator
    from .tool_based_agent import ToolBasedAgent

# 全局代理实例缓存
_agent_instances = {}

# ===========================================
# 核心Agent导入和导出
# ===========================================

# 导出核心Agent类
from .autoreport_ai_agent import AutoReportAIAgent
from .placeholder_to_sql_agent import PlaceholderToSqlAgent
from .task_supplement_agent import TaskSupplementAgent  
from .multi_context_integrator import MultiContextIntegrator
from .sql_testing_validator import SqlTestingValidator
from .tool_based_agent import ToolBasedAgent

# ===========================================
# Agent实例获取服务
# ===========================================

async def get_autoreport_ai_agent() -> 'AutoReportAIAgent':
    """获取AutoReportAI Agent主编排器"""
    if 'autoreport_ai_agent' not in _agent_instances:
        _agent_instances['autoreport_ai_agent'] = AutoReportAIAgent()
    return _agent_instances['autoreport_ai_agent']

async def get_placeholder_to_sql_agent() -> 'PlaceholderToSqlAgent':
    """获取占位符→SQL转换Agent"""
    if 'placeholder_to_sql_agent' not in _agent_instances:
        _agent_instances['placeholder_to_sql_agent'] = PlaceholderToSqlAgent()
    return _agent_instances['placeholder_to_sql_agent']

async def get_task_supplement_agent() -> 'TaskSupplementAgent':
    """获取任务补充Agent"""
    if 'task_supplement_agent' not in _agent_instances:
        _agent_instances['task_supplement_agent'] = TaskSupplementAgent()
    return _agent_instances['task_supplement_agent']

async def get_multi_context_integrator() -> 'MultiContextIntegrator':
    """获取多上下文集成器"""
    if 'multi_context_integrator' not in _agent_instances:
        _agent_instances['multi_context_integrator'] = MultiContextIntegrator()
    return _agent_instances['multi_context_integrator']

async def get_sql_testing_validator() -> 'SQLTestingValidator':
    """获取SQL测试验证器"""
    if 'sql_testing_validator' not in _agent_instances:
        _agent_instances['sql_testing_validator'] = SQLTestingValidator()
    return _agent_instances['sql_testing_validator']

async def get_tool_based_agent() -> 'ToolBasedAgent':
    """获取基于工具的Agent"""
    if 'tool_based_agent' not in _agent_instances:
        _agent_instances['tool_based_agent'] = ToolBasedAgent()
    return _agent_instances['tool_based_agent']

# ===========================================
# 导出接口
# ===========================================

__all__ = [
    # 核心Agent类
    'AutoReportAIAgent',
    'PlaceholderToSQLAgent',
    'TaskSupplementAgent', 
    'MultiContextIntegrator',
    'SQLTestingValidator',
    'ToolBasedAgent',
    
    # Agent实例获取服务
    'get_autoreport_ai_agent',
    'get_placeholder_to_sql_agent',
    'get_task_supplement_agent',
    'get_multi_context_integrator',
    'get_sql_testing_validator',
    'get_tool_based_agent'
]