"""
表结构管理模块

提供数据源表结构的发现、存储、分析和查询功能
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .schema_discovery_service import SchemaDiscoveryService
from .schema_analysis_service import SchemaAnalysisService
from .schema_query_service import SchemaQueryService
from .schema_metadata_service import SchemaMetadataService

# 导入工具类
from .utils.relationship_analyzer import RelationshipAnalyzer
from .utils.type_normalizer import TypeNormalizer

# 模块导出
__all__ = [
    "SchemaDiscoveryService",
    "SchemaAnalysisService", 
    "SchemaQueryService",
    "SchemaMetadataService",
    "RelationshipAnalyzer",
    "TypeNormalizer"
]
