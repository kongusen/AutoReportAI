"""
Application Layer - DDD架构v2.0统一应用层

基于DDD架构和Agent系统成功经验的应用层：
- base: 基础应用服务架构
- tasks: 任务应用服务
- reporting: 报告应用服务
- llm: LLM编排服务
- orchestrators: 复杂业务编排
- services: 业务应用服务
- context: 上下文构建器
"""

# 基础应用服务架构
from .base_application_service import (
    BaseApplicationService,
    TransactionalApplicationService,
    ApplicationResult,
    OperationResult,
    PaginationRequest,
    PaginationResult,
    event_publisher,
    register_application_service,
    get_application_service,
    list_application_services
)

# 任务应用服务
from .tasks import (
    TaskApplicationService,
    TaskExecutionService
)

# 报告应用服务
from .reporting import (
    ReportApplicationService
)

# LLM编排服务
from .llm import (
    LLMOrchestrationService,
    get_llm_orchestration_service
)

# 复杂业务编排
from .orchestrators import (
    ReportOrchestrator,
    DataOrchestrator
)

# 业务应用服务
from .services import (
    WorkflowApplicationService,
    ContextAwareApplicationService
)

# 上下文构建器 - 核心三大构建器
from .context import (
    DataSourceContextBuilder,
    TemplateContextBuilder,
    TaskDrivenContextBuilder,
    ContextCoordinator,
    Context
)

# Agent Input 构建与桥接
from .agent_input import AgentInputBridge, AgentInputBuilder

__all__ = [
    # 基础架构
    "BaseApplicationService",
    "TransactionalApplicationService", 
    "ApplicationResult",
    "OperationResult",
    "PaginationRequest",
    "PaginationResult",
    "event_publisher",
    "register_application_service",
    "get_application_service",
    "list_application_services",
    
    # 任务应用服务
    "TaskApplicationService",
    "TaskExecutionService",
    
    # 报告应用服务
    "ReportApplicationService",
    
    # LLM编排服务
    "LLMOrchestrationService",
    "get_llm_orchestration_service",
    
    # 复杂业务编排
    "ReportOrchestrator",
    "DataOrchestrator",
    
    # 业务应用服务
    "WorkflowApplicationService",
    "ContextAwareApplicationService",
    
    # 上下文构建器
    "DataSourceContextBuilder",
    "TemplateContextBuilder",
    "TaskDrivenContextBuilder",
    "ContextCoordinator",
    "Context",
    # 桥接服务
    "AgentInputBridge",
    "AgentInputBuilder",
]

# 自动注册核心应用服务
_task_service = TaskApplicationService()
_report_service = ReportApplicationService()

register_application_service("task", _task_service)
register_application_service("report", _report_service)
