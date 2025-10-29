"""
Schema 工具库

提供 Schema 发现、检索和缓存功能
"""

from .discovery import (
    SchemaDiscoveryTool,
    TableInfo,
    ColumnInfo,
    RelationshipInfo,
    create_schema_discovery_tool
)

from .retrieval import (
    SchemaRetrievalTool,
    RetrievalQuery,
    RetrievalResult,
    create_schema_retrieval_tool
)

from .cache import (
    SchemaCacheTool,
    SchemaCacheManager,
    CacheEntry,
    CacheStats,
    create_schema_cache_tool,
    create_schema_cache_manager
)

# 导出
__all__ = [
    # Discovery
    "SchemaDiscoveryTool",
    "TableInfo",
    "ColumnInfo",
    "RelationshipInfo",
    "create_schema_discovery_tool",
    
    # Retrieval
    "SchemaRetrievalTool",
    "RetrievalQuery",
    "RetrievalResult",
    "create_schema_retrieval_tool",
    
    # Cache
    "SchemaCacheTool",
    "SchemaCacheManager",
    "CacheEntry",
    "CacheStats",
    "create_schema_cache_tool",
    "create_schema_cache_manager",
]