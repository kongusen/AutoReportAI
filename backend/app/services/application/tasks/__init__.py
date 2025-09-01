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

# 注意：这里只导出编排任务，不包含具体业务逻辑
try:
    from .orchestration_tasks import (
        orchestrate_report_generation,
        orchestrate_data_processing,
        orchestrate_context_aware_task
    )
    
    __all__ = [
        'orchestrate_report_generation', 
        'orchestrate_data_processing',
        'orchestrate_context_aware_task'
    ]
except ImportError:
    # 编排任务还未创建时的占位符
    __all__ = []

__version__ = "2.0.0"