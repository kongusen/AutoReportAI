"""
Services module - 统一架构

基于Agent系统成功经验的统一服务架构：
- application: 应用层（核心业务编排）
- domain: 领域层（业务逻辑）
- infrastructure: 基础设施层（Agent系统、缓存、存储等）
- data: 数据访问层
"""

# =============================================================================
# 统一架构分层导入
# =============================================================================

# 应用层 - 核心编排
from . import application

# 领域层 - 业务逻辑
from . import domain

# 基础设施层 - Agent系统与技术服务
from . import infrastructure

# 数据层 - 数据访问
from . import data

# =============================================================================
# 核心服务导入 - 基于Agent系统架构
# =============================================================================

# Agent系统 - 核心编排引擎
from .infrastructure.agents import execute_agent_task
from .infrastructure.agents.core import AgentCoordinator

# 数据服务
from .data.processing.analysis import DataAnalysisService
from .data.sources.data_source_service import DataSourceService
from .data.connectors.doris_connector import DorisConnector

# 领域服务
from .domain.reporting.generator import ReportGenerationService

# 应用层服务
from .application.tasks.task_application_service import TaskApplicationService
from .application.llm.llm_orchestration_service import LLMOrchestrationService

# 基础设施服务
from .infrastructure.notification.notification_service import NotificationService
from .infrastructure.storage.file_storage_service import FileStorageService
from .infrastructure.llm.simple_model_selector import SimpleModelSelector as LLMService

__all__ = [
    # =========================================================================
    # 统一架构分层模块
    # =========================================================================
    "application",      # 应用层
    "domain",           # 领域层
    "infrastructure",   # 基础设施层
    "data",             # 数据层
    
    # =========================================================================
    # Agent系统核心服务
    # =========================================================================
    "execute_agent_task",
    "AgentCoordinator",
    
    # =========================================================================
    # 核心业务服务
    # =========================================================================
    
    # 数据服务
    "DataAnalysisService",
    "DataSourceService",
    "DorisConnector",
    
    # 领域服务
    "ReportGenerationService",
    
    # 应用服务
    "TaskApplicationService",
    "LLMOrchestrationService",
    
    # 基础设施服务
    "LLMService",
    "NotificationService", 
    "FileStorageService",
]