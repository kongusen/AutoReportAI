"""
Schema Management Module

架构管理模块，合并了原有的schemas和schema_management功能：
- schema_service: 核心架构服务
- query_builder: 查询构建器
- schema_discovery_service: 架构发现服务
- schema_analysis_service: 架构分析服务
- schema_metadata_service: 架构元数据服务
- schema_query_service: 架构查询服务
- utils: 工具类（关系分析器、类型标准化器）
"""

# 模块版本
__version__ = "2.0.0"

# 核心架构服务（原schemas目录）
from .schema_service import (
    SchemaDiscoveryService as CoreSchemaDiscoveryService, 
    SchemaAnalysisService as CoreSchemaAnalysisService, 
    DatabaseSchema, TableSchema, get_schema_service
)

# 查询构建器（原schemas目录）
from .query_builder import (
    SchemaAwareQueryBuilder, NaturalLanguageQueryBuilder, QueryContext, QueryType
)

# 扩展架构服务（原schema_management目录）
from .schema_discovery_service import SchemaDiscoveryService
# TEMPORARILY DISABLED: SchemaAnalysisService - Legacy IAOP dependencies removed
# from .schema_analysis_service import SchemaAnalysisService
from .schema_query_service import SchemaQueryService
from .schema_metadata_service import SchemaMetadataService

# 导入工具类
from .utils.relationship_analyzer import RelationshipAnalyzer
from .utils.type_normalizer import TypeNormalizer

# 模块导出
__all__ = [
    # 核心架构服务
    "CoreSchemaDiscoveryService",
    "CoreSchemaAnalysisService",
    "DatabaseSchema",
    "TableSchema", 
    "get_schema_service",
    
    # 查询构建器
    "SchemaAwareQueryBuilder",
    "NaturalLanguageQueryBuilder",
    "QueryContext",
    "QueryType",
    
    # 扩展架构服务
    "SchemaDiscoveryService",
    # "SchemaAnalysisService",  # TEMPORARILY DISABLED
    "SchemaQueryService",
    "SchemaMetadataService",
    
    # 工具类
    "RelationshipAnalyzer",
    "TypeNormalizer"
]
