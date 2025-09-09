"""
Application Layer - DDD Architecture

DDD架构应用层，包含：
- services: 应用服务（协调业务流程）
- orchestrators: 编排器（复杂工作流管理）  
- tasks: 编排任务（分布式任务编排）
- context: 上下文构建器
- facades: 统一服务门面
"""

# 应用服务
from .services import (
    ReportApplicationService, 
    WorkflowApplicationService,
    ContextAwareApplicationService
)

# 任务服务（从 tasks 目录导入）
from .tasks import (
    TaskApplicationService,
    TaskExecutionService
)

# 编排器
from .orchestrators import (
    ReportOrchestrator,
    DataOrchestrator
)

# 编排任务
from .tasks import (
    orchestrate_report_generation,
    orchestrate_data_processing
)

# 上下文构建器
from .context import (
    TimeContextBuilder,
    BusinessContextBuilder,
    DocumentContextBuilder
)

# 统一服务门面
try:
    from .facades.unified_service_facade import get_unified_facade
    _HAS_FACADES = True
except ImportError:
    _HAS_FACADES = False

__all__ = [
    # 应用服务
    "ReportApplicationService", 
    "WorkflowApplicationService",
    "ContextAwareApplicationService",
    
    # 任务服务
    "TaskApplicationService",
    "TaskExecutionService",
    
    # 编排器
    "ReportOrchestrator",
    "DataOrchestrator",
    
    # 编排任务
    "orchestrate_report_generation",
    "orchestrate_data_processing", 
    
    # 上下文构建器
    "TimeContextBuilder",
    "BusinessContextBuilder", 
    "DocumentContextBuilder",
]

# 可选门面支持
if _HAS_FACADES:
    __all__.append("get_unified_facade")