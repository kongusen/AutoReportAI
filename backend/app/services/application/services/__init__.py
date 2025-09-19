"""
Application Services - DDD架构v2.0

应用服务层，负责：
1. 协调Domain层的业务逻辑
2. 编排跨领域的工作流
3. 处理应用级的用例场景
4. 管理事务边界

遵循DDD原则：
- 薄薄的一层，不包含业务逻辑
- 编排Domain服务和Infrastructure服务
- 处理应用级的横切关注点
- 通过基础设施层调用agents，而非直接实现agents

注意：agents已正确移至基础设施层(infrastructure/agents)，
      业务逻辑通过领域服务访问agents技术实现
"""

from .workflow_service import WorkflowApplicationService
from .context_aware_service import ContextAwareApplicationService

__all__ = [
    'WorkflowApplicationService',
    'ContextAwareApplicationService'
]

# 注意：ReportApplicationService已移至reporting/report_application_service.py
# 作为专门的报告应用服务，遵循DDD架构v2.0规范