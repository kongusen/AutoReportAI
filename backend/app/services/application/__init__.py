"""
Application Layer

应用层入口，提供统一的服务编排和门面：
- orchestration: 服务编排
- workflows: 工作流
- facades: 统一门面
- factories: 工厂模式
- task_management: 任务管理
- interfaces: 接口定义
"""

# 主要的应用层组件
from .orchestration.service_orchestrator import (
    ServiceOrchestrator, 
    OrchestrationMode, 
    ServiceContext
)
from .orchestration.workflow_engine import (
    WorkflowEngine,
    WorkflowDefinition,
    StepDefinition,
    StepType,
    WorkflowStatus,
    StepStatus
)
from .facades.unified_service_facade import (
    UnifiedServiceFacade,
    get_global_facade,
    cleanup_global_facade
)

# 任务管理
from .task_management.application.services.task_application_service import (
    TaskApplicationService
)
from .task_management.execution.two_phase_pipeline import (
    execute_two_phase_pipeline, PipelineConfiguration
)

# 接口定义
from .interfaces.extraction_interfaces import (
    PlaceholderExtractorInterface, DocumentPipelineInterface
)

__all__ = [
    # 服务编排
    "ServiceOrchestrator",
    "OrchestrationMode", 
    "ServiceContext",
    
    # 工作流引擎
    "WorkflowEngine",
    "WorkflowDefinition",
    "StepDefinition", 
    "StepType",
    "WorkflowStatus",
    "StepStatus",
    
    # 统一门面
    "UnifiedServiceFacade",
    "get_global_facade",
    "cleanup_global_facade",
    
    # 任务管理
    "TaskApplicationService",
    "execute_two_phase_pipeline",
    "PipelineConfiguration",
    
    # 接口定义
    "PlaceholderExtractorInterface",
    "DocumentPipelineInterface",
]