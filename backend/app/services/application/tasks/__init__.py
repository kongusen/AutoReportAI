"""
Application层编排任务

注意：这些任务与传统的Celery任务不同
- 不包含具体的业务逻辑
- 专注于编排其他层的任务
- 管理跨领域的工作流程
- 处理任务间的依赖关系

职责：
1. 编排Domain、Data、Infrastructure层的任务
2. 管理分布式工作流的状态
3. 处理任务链和任务组
4. 协调事务边界
"""

# 任务应用服务
from .task_application_service import TaskApplicationService
from .task_execution_service import TaskExecutionService

# 编排任务
try:
    from .orchestration_tasks import (
        orchestrate_report_generation,
        orchestrate_data_processing,
        orchestrate_context_aware_task
    )
    
    _orchestration_tasks = [
        'orchestrate_report_generation', 
        'orchestrate_data_processing',
        'orchestrate_context_aware_task'
    ]
except ImportError:
    # 编排任务还未创建时的占位符
    _orchestration_tasks = []

# 导出所有任务相关组件
__all__ = [
    # 任务服务
    'TaskApplicationService',
    'TaskExecutionService',
] + _orchestration_tasks

__version__ = "2.0.0"