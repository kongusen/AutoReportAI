"""
Application层Agent服务

负责协调Domain层和Infrastructure层的服务，实现复杂的工作流编排。

Application层的Agent职责：
1. 工作流编排和协调
2. 跨领域服务集成
3. 上下文管理和传递
4. 任务状态跟踪

不应包含：
- 具体的业务逻辑（属于Domain层）
- 技术实现细节（属于Infrastructure层）
- 数据访问逻辑（属于Data层）
"""

# 延迟导入避免循环依赖
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .workflow_orchestration_agent import WorkflowOrchestrationAgent
    from .task_coordination_agent import TaskCoordinationAgent
    from .context_aware_agent import ContextAwareAgent

# 全局服务实例缓存
_agent_instances = {}

async def get_workflow_orchestration_agent() -> 'WorkflowOrchestrationAgent':
    """获取工作流编排代理实例"""
    if 'workflow_orchestration' not in _agent_instances:
        from .workflow_orchestration_agent import WorkflowOrchestrationAgent
        _agent_instances['workflow_orchestration'] = WorkflowOrchestrationAgent()
    return _agent_instances['workflow_orchestration']

async def get_task_coordination_agent() -> 'TaskCoordinationAgent':
    """获取任务协调代理实例"""
    if 'task_coordination' not in _agent_instances:
        from .task_coordination_agent import TaskCoordinationAgent
        _agent_instances['task_coordination'] = TaskCoordinationAgent()
    return _agent_instances['task_coordination']

async def get_context_aware_agent() -> 'ContextAwareAgent':
    """获取上下文感知代理实例"""
    if 'context_aware' not in _agent_instances:
        from .context_aware_agent import ContextAwareAgent
        _agent_instances['context_aware'] = ContextAwareAgent()
    return _agent_instances['context_aware']

__all__ = [
    'get_workflow_orchestration_agent',
    'get_task_coordination_agent', 
    'get_context_aware_agent'
]