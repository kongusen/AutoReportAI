"""
Infrastructure层AI智能代理服务

提供DAG编排、执行引擎和智能代理的基础设施支撑：

核心组件：
1. DAGController - DAG编排和流程控制
2. AIExecutionEngine - AI任务执行引擎
3. TaskContext - 任务上下文管理
4. ReactAgent - 纯数据库驱动React模式智能代理（需要user_id）

技术职责：
- 提供AI执行的技术基础设施
- 管理DAG编排和步骤控制
- 处理模型调度和资源管理
- 支撑上层业务代理的技术需求

不包含业务逻辑，专注于技术实现层面。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dag_controller import DAGController
    from .execution_engine import AIExecutionEngine  
    from .task_context import AITaskContext
    from .react_agent import ReactAgent

# 延迟导入和服务获取
_agent_instances = {}

# 导出核心类用于直接导入
from .data_transformation_agent import DataTransformationAgent, create_data_transformation_agent
from .dag_controller import (
    DAGController, 
    ControlContext, 
    ControlDecision, 
    ExecutionStatus, 
    StepResult,
    create_control_context
)
from .execution_engine import AIExecutionEngine
from .task_context import (
    AITaskContext, 
    ExecutionStep, 
    ExecutionStepType, 
    ModelRequirement, 
    TaskComplexity,
    create_ai_task_context_from_placeholder_analysis
)
from .react_agent import ReactAgent

async def get_dag_controller() -> 'DAGController':
    """获取DAG编排控制器"""
    if 'dag_controller' not in _agent_instances:
        from .dag_controller import DAGController
        _agent_instances['dag_controller'] = DAGController()
    return _agent_instances['dag_controller']

async def get_ai_execution_engine() -> 'AIExecutionEngine':
    """获取AI执行引擎"""
    if 'execution_engine' not in _agent_instances:
        from .execution_engine import AIExecutionEngine
        _agent_instances['execution_engine'] = AIExecutionEngine()
    return _agent_instances['execution_engine']

async def get_ai_task_context() -> 'AITaskContext':
    """获取AI任务上下文管理器"""
    if 'task_context' not in _agent_instances:
        from .task_context import AITaskContext
        _agent_instances['task_context'] = AITaskContext()
    return _agent_instances['task_context']

def create_react_agent(user_id: str) -> 'ReactAgent':
    """
    创建React智能代理
    注意：每个用户需要独立的agent实例
    """
    if not user_id:
        raise ValueError("user_id is required for ReactAgent")
    
    from .react_agent import ReactAgent
    return ReactAgent(user_id=user_id)

__all__ = [
    'get_dag_controller',
    'get_ai_execution_engine',
    'get_ai_task_context', 
    'create_react_agent',
    'ReactAgent',
    'create_data_transformation_agent',
    'DataTransformationAgent',
    'DAGController',
    'AIExecutionEngine',
    'AITaskContext'
]