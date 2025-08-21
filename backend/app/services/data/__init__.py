"""
数据层入口

包含完整的数据访问层功能：
- connectors: 数据连接器
- repositories: 数据仓储
- schemas: 架构管理（合并了schema_management）
- sources: 数据源管理  
- processing: 数据处理
"""

from . import connectors, repositories, sources, schemas
# 现在恢复processing模块
from . import processing

# Repository层
from .repositories.base_repository import BaseRepository, RepositoryInterface, TransactionalRepository
from .repositories.template_repository import TemplateRepository
from .repositories.placeholder_repository import PlaceholderRepository, PlaceholderValueRepository
from .repositories.data_source_repository import DataSourceRepository

# Connector层
from .connectors.connector_factory import create_connector
from .connectors.base_connector import BaseConnector

# Schema层（合并后） - 先只导入基础类
from .schemas.schema_service import (
    DatabaseSchema, TableSchema
)
# 暂时注释掉其他schema导入，先让基础服务启动
# from .schemas.query_builder import (
#     SchemaAwareQueryBuilder, NaturalLanguageQueryBuilder, QueryContext, QueryType
# )

# 数据源服务
from .sources.data_source_service import DataSourceService

# 恢复processing导入
from .processing.analysis import DataAnalysisService
from .processing.retrieval import DataRetrievalService
from .processing.statistics_service import StatisticsService

__all__ = [
    # 模块
    "connectors",
    "repositories", 
    "sources",
    "schemas",
    "processing",
    
    # Repository层
    "BaseRepository",
    "RepositoryInterface", 
    "TransactionalRepository",
    "TemplateRepository",
    "PlaceholderRepository",
    "PlaceholderValueRepository",
    "DataSourceRepository",
    
    # Connector层
    "create_connector",
    "BaseConnector",
    
    # Schema层（基础类）
    "DatabaseSchema",
    "TableSchema",
    
    # 数据源服务
    "DataSourceService",
    
    # 数据处理服务
    "DataAnalysisService",
    "DataRetrievalService",
    "StatisticsService",
]


