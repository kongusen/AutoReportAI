"""
Schema Service - 已重构

此文件已重构为向现代schema服务的重定向服务
所有schema相关功能已整合到专门的服务中:

- SchemaAnalysisService -> schema_analysis_service.py
- SchemaDiscoveryService -> schema_discovery_service.py  
- SchemaQueryService -> schema_query_service.py
- SchemaMetadataService -> schema_metadata_service.py

本文件保留用于向后兼容性。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# 向后兼容的重定向函数
def get_schema_service():
    """获取Schema发现服务 - 重定向到现代实现"""
    logger.warning("get_schema_service() is deprecated, use create_schema_discovery_service() instead")
    from .schema_discovery_service import SchemaDiscoveryService
    from app.db.session import get_db_session
    
    # 返回带数据库会话的现代实现
    with get_db_session() as db:
        return SchemaDiscoveryService(db)


def create_schema_discovery_service(db_session, user_id: str = None):
    """创建Schema发现服务"""
    from .schema_discovery_service import SchemaDiscoveryService
    return SchemaDiscoveryService(db_session)


def create_unified_schema_service(db_session, user_id: str):
    """创建统一的Schema服务"""
    if not user_id:
        raise ValueError("user_id is required for unified schema service")
    
    from .schema_analysis_service import create_schema_analysis_service
    from .schema_discovery_service import SchemaDiscoveryService
    from .schema_query_service import SchemaQueryService
    
    return {
        "analysis": create_schema_analysis_service(db_session, user_id),
        "discovery": SchemaDiscoveryService(db_session),
        "query": SchemaQueryService(db_session)
    }


# 向后兼容的模型重定向
class DatabaseSchema:
    """Database Schema 模型重定向"""
    def __init__(self):
        logger.warning("DatabaseSchema from schema_service.py is deprecated, use app.models.table_schema.Database directly")
        from app.models.table_schema import Database
        self._model = Database

class TableSchema:
    """Table Schema 模型重定向"""  
    def __init__(self):
        logger.warning("TableSchema from schema_service.py is deprecated, use app.models.table_schema.TableSchema directly")
        from app.models.table_schema import TableSchema as TableSchemaModel
        self._model = TableSchemaModel

# 向后兼容的类重定向
class SchemaDiscoveryService:
    """Schema发现服务 - 重定向到现代实现"""
    
    def __init__(self, db_session):
        logger.warning("Importing SchemaDiscoveryService from schema_service.py is deprecated, use schema_discovery_service.py directly")
        from .schema_discovery_service import SchemaDiscoveryService as ModernSchemaDiscoveryService
        self._service = ModernSchemaDiscoveryService(db_session)
    
    def __getattr__(self, name):
        return getattr(self._service, name)


class SchemaAnalysisService:
    """Schema分析服务 - 重定向到现代实现"""
    
    def __init__(self, db_session, user_id: str = None):
        logger.warning("Importing SchemaAnalysisService from schema_service.py is deprecated, use schema_analysis_service.py directly")
        if not user_id:
            raise ValueError("user_id is required for Schema Analysis Service")
        from .schema_analysis_service import SchemaAnalysisService as ModernSchemaAnalysisService
        self._service = ModernSchemaAnalysisService(db_session, user_id)
    
    def __getattr__(self, name):
        return getattr(self._service, name)


# 废弃的类定义，仅保留用于向后兼容
class LegacySchemaAnalysisService:
    """Legacy Schema分析服务 - 已废弃"""
    
    def __init__(self):
        logger.warning("LegacySchemaAnalysisService is deprecated")
    
    async def analyze_relationships(self, schema):
        """已废弃的方法"""
        logger.warning("analyze_relationships() is deprecated, use schema_analysis_service.py")
        return {}
    
    async def analyze_data_types(self, schema):
        """已废弃的方法"""
        logger.warning("analyze_data_types() is deprecated, use schema_analysis_service.py")
        return {}
    
    async def suggest_optimizations(self, schema):
        """已废弃的方法"""
        logger.warning("suggest_optimizations() is deprecated, use schema_analysis_service.py")
        return []


# 导出重定向函数
__all__ = [
    "get_schema_service",
    "create_schema_discovery_service", 
    "create_unified_schema_service",
    "DatabaseSchema",
    "TableSchema",
    "SchemaDiscoveryService",
    "SchemaAnalysisService",
    "LegacySchemaAnalysisService"
]