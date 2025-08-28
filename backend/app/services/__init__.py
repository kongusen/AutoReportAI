"""
Services module

重构后的分层架构服务模块：
- data: 数据访问层
- domain: 领域层  
- infrastructure: 基础设施层
- application: 应用层
- ai: AI层
"""

# =============================================================================
# 分层架构导入
# =============================================================================

# 数据层
from . import data

# 领域层
from . import domain

# 基础设施层 
from . import infrastructure

# 应用层
from . import application

# IAOP核心平台（替代AI层）
from . import iaop

# =============================================================================
# 向后兼容导入 (Backward Compatibility)
# =============================================================================

# 关键服务的向后兼容导入
from .data.processing.analysis import DataAnalysisService
from .data.processing.retrieval import DataRetrievalService
from .data.processing.statistics_service import StatisticsService
from .data.sources.data_source_service import DataSourceService
from .data.connectors.doris_connector import DorisConnector

# 领域服务向后兼容
from .domain.template.template_service import TemplateService
from .domain.reporting.generator import ReportGenerationService

# IAOP服务向后兼容（直接使用核心平台）
from .llm.client import LLMServerClient as LLMService
from .iaop.agents.specialized.placeholder_parser_agent import PlaceholderParserAgent as PlaceholderSQLAgent
from .iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent as PlaceholderSQLAnalyzer

# 应用服务向后兼容
from .application.task_management.execution.two_phase_pipeline import execute_two_phase_pipeline

# 基础设施服务向后兼容  
# PipelineCacheManager已被统一缓存系统替代
from .infrastructure.notification.notification_service import NotificationService
from .infrastructure.storage.file_storage_service import FileStorageService

__all__ = [
    # =========================================================================
    # 分层架构模块
    # =========================================================================
    "data",           # 数据访问层
    "domain",         # 领域层
    "infrastructure", # 基础设施层  
    "application",    # 应用层
    "iaop",          # IAOP核心平台
    
    # =========================================================================
    # 向后兼容导出
    # =========================================================================
    
    # 数据服务
    "DataAnalysisService",
    "DataRetrievalService", 
    "StatisticsService",
    "DataSourceService",
    "DorisConnector",
    
    # 领域服务
    "TemplateService",
    "ReportGenerationService",
    
    # IAOP服务  
    "LLMService",
    "PlaceholderSQLAgent",
    "PlaceholderSQLAnalyzer",
    
    # 应用服务
    "execute_two_phase_pipeline",
    
    # 基础设施服务
    "NotificationService", 
    "FileStorageService",
]