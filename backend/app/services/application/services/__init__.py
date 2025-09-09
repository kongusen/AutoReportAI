"""
Application Services

应用服务层，负责：
1. 协调Domain层的业务逻辑
2. 编排跨领域的工作流
3. 处理应用级的用例场景
4. 管理事务边界

遵循DDD原则：
- 薄薄的一层，不包含业务逻辑
- 编排Domain服务和Infrastructure服务
- 处理应用级的横切关注点
"""

from .report_service import ReportApplicationService
from .workflow_service import WorkflowApplicationService
from .context_aware_service import ContextAwareApplicationService

__all__ = [
    'ReportApplicationService', 
    'WorkflowApplicationService',
    'ContextAwareApplicationService'
]