"""
Services module

React Agent架构服务模块：
- data: 数据访问层
- domain: 领域层  
- infrastructure: 基础设施层
- application: 应用层
"""

# =============================================================================
# React Agent DDD分层架构导入
# =============================================================================

# 数据层
from . import data

# 领域层
from . import domain

# 基础设施层 
from . import infrastructure

# 应用层
from . import application

# =============================================================================
# React Agent核心服务导入
# =============================================================================

# 数据服务
from .data.processing.analysis import DataAnalysisService
from .data.processing.retrieval import DataRetrievalService
from .data.processing.statistics_service import StatisticsService
from .data.sources.data_source_service import DataSourceService
from .data.connectors.doris_connector import DorisConnector

# 领域服务
from .domain.reporting.generator import ReportGenerationService

# React Agent应用层服务
from .application.agents import get_workflow_orchestration_agent
from .application.agents.task_coordination_agent import get_task_coordination_agent
from .application.agents.context_aware_agent import get_context_aware_agent

# 通知服务 (已迁移到新架构)
from .infrastructure.notification.notification_service import NotificationService
from .infrastructure.storage.file_storage_service import FileStorageService

# LLM服务 (已迁移到新架构)
from .infrastructure.ai.llm.simple_model_selector import SimpleModelSelector as LLMService

__all__ = [
    # =========================================================================
    # React Agent DDD分层架构模块
    # =========================================================================
    "data",           # 数据访问层
    "domain",         # 领域层
    "infrastructure", # 基础设施层  
    "application",    # 应用层
    
    # =========================================================================
    # React Agent应用层服务
    # =========================================================================
    "get_workflow_orchestration_agent",
    "get_task_coordination_agent", 
    "get_context_aware_agent",
    
    # =========================================================================
    # React Agent核心服务导出
    # =========================================================================
    
    # 数据服务
    "DataAnalysisService",
    "DataRetrievalService", 
    "StatisticsService",
    "DataSourceService",
    "DorisConnector",
    
    # 领域服务
    "ReportGenerationService",
    
    # LLM服务
    "LLMService",
    
    # 基础设施服务
    "NotificationService", 
    "FileStorageService",
]