"""
Schema Service

统一的schema管理服务，整合原有的schema_management功能
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..connectors.connector_factory import create_connector

logger = logging.getLogger(__name__)


@dataclass
class TableSchema:
    """表schema定义"""
    name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    table_type: str = "table"  # table, view, materialized_view
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseSchema:
    """数据库schema定义"""
    database_name: str
    tables: Dict[str, TableSchema] = field(default_factory=dict)
    views: Dict[str, TableSchema] = field(default_factory=dict)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: Optional[datetime] = None


class SchemaCache:
    """Schema缓存管理"""
    
    def __init__(self, cache_ttl_seconds: int = 3600):  # 1小时缓存
        self.cache_ttl = cache_ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
    
    def get(self, data_source_id: str) -> Optional[DatabaseSchema]:
        """获取缓存的schema"""
        if data_source_id not in self.cache:
            return None
        
        # 检查是否过期
        cache_time = self.cache_timestamps.get(data_source_id)
        if cache_time:
            elapsed = (datetime.now() - cache_time).total_seconds()
            if elapsed > self.cache_ttl:
                self.invalidate(data_source_id)
                return None
        
        try:
            cache_data = self.cache[data_source_id]
            return DatabaseSchema(**cache_data)
        except Exception as e:
            logger.warning(f"Failed to deserialize cached schema for {data_source_id}: {e}")
            self.invalidate(data_source_id)
            return None
    
    def set(self, data_source_id: str, schema: DatabaseSchema):
        """设置缓存"""
        try:
            # 序列化schema对象
            cache_data = {
                'database_name': schema.database_name,
                'tables': {name: self._serialize_table(table) for name, table in schema.tables.items()},
                'views': {name: self._serialize_table(view) for name, view in schema.views.items()},
                'functions': schema.functions,
                'metadata': schema.metadata,
                'last_updated': schema.last_updated
            }
            
            self.cache[data_source_id] = cache_data
            self.cache_timestamps[data_source_id] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to cache schema for {data_source_id}: {e}")
    
    def invalidate(self, data_source_id: str):
        """使缓存失效"""
        self.cache.pop(data_source_id, None)
        self.cache_timestamps.pop(data_source_id, None)
    
    def clear_all(self):
        """清空所有缓存"""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def _serialize_table(self, table: TableSchema) -> Dict[str, Any]:
        """序列化表schema"""
        return {
            'name': table.name,
            'columns': table.columns,
            'primary_keys': table.primary_keys,
            'foreign_keys': table.foreign_keys,
            'indexes': table.indexes,
            'table_type': table.table_type,
            'comment': table.comment,
            'metadata': table.metadata
        }


class SchemaDiscoveryService:
    """Schema发现服务"""
    
    def __init__(self):
        self.connector_manager = get_connector_manager()
        self.cache = SchemaCache()
    
    async def discover_schema(self, data_source_id: str, connector_type: str,
                            config: Dict[str, Any], force_refresh: bool = False) -> Optional[DatabaseSchema]:
        """发现数据源的schema"""
        # 检查缓存
        if not force_refresh:
            cached_schema = self.cache.get(data_source_id)
            if cached_schema:
                logger.debug(f"Using cached schema for data source: {data_source_id}")
                return cached_schema
        
        try:
            # 获取连接器
            connector = await self.connector_manager.get_connector(
                data_source_id, connector_type, config
            )
            
            if not connector:
                logger.error(f"Failed to create connector for data source: {data_source_id}")
                return None
            
            # 发现schema
            schema = await self._discover_from_connector(connector, data_source_id)
            
            # 释放连接器
            await self.connector_manager.release_connector(data_source_id, connector)
            
            # 缓存结果
            if schema:
                self.cache.set(data_source_id, schema)
            
            return schema
            
        except Exception as e:
            logger.error(f"Schema discovery failed for {data_source_id}: {e}")
            return None
    
    async def _discover_from_connector(self, connector, data_source_id: str) -> Optional[DatabaseSchema]:
        """从连接器发现schema"""
        try:
            # 获取数据库信息
            database_info = await self._get_database_info(connector)
            
            # 获取表信息
            tables = await self._get_tables_info(connector)
            
            # 获取视图信息
            views = await self._get_views_info(connector)
            
            # 获取函数信息（如果支持）
            functions = await self._get_functions_info(connector)
            
            # 构建schema对象
            schema = DatabaseSchema(
                database_name=database_info.get('name', data_source_id),
                tables=tables,
                views=views,
                functions=functions,
                metadata=database_info,
                last_updated=datetime.now()
            )
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to discover schema from connector: {e}")
            return None
    
    async def _get_database_info(self, connector) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            if hasattr(connector, 'get_database_info'):
                return await connector.get_database_info()
            else:
                return {'name': 'unknown', 'version': 'unknown'}
        except Exception as e:
            logger.warning(f"Failed to get database info: {e}")
            return {}
    
    async def _get_tables_info(self, connector) -> Dict[str, TableSchema]:
        """获取表信息"""
        tables = {}
        
        try:
            if hasattr(connector, 'get_tables'):
                table_list = await connector.get_tables()
                
                for table_info in table_list:
                    table_name = table_info.get('name')
                    if not table_name:
                        continue
                    
                    # 获取列信息
                    columns = await self._get_table_columns(connector, table_name)
                    
                    # 获取主键信息
                    primary_keys = await self._get_primary_keys(connector, table_name)
                    
                    # 获取外键信息
                    foreign_keys = await self._get_foreign_keys(connector, table_name)
                    
                    # 获取索引信息
                    indexes = await self._get_indexes(connector, table_name)
                    
                    table_schema = TableSchema(
                        name=table_name,
                        columns=columns,
                        primary_keys=primary_keys,
                        foreign_keys=foreign_keys,
                        indexes=indexes,
                        table_type=table_info.get('type', 'table'),
                        comment=table_info.get('comment'),
                        metadata=table_info
                    )
                    
                    tables[table_name] = table_schema
                    
        except Exception as e:
            logger.error(f"Failed to get tables info: {e}")
        
        return tables
    
    async def _get_views_info(self, connector) -> Dict[str, TableSchema]:
        """获取视图信息"""
        views = {}
        
        try:
            if hasattr(connector, 'get_views'):
                view_list = await connector.get_views()
                
                for view_info in view_list:
                    view_name = view_info.get('name')
                    if not view_name:
                        continue
                    
                    # 获取列信息
                    columns = await self._get_table_columns(connector, view_name)
                    
                    view_schema = TableSchema(
                        name=view_name,
                        columns=columns,
                        table_type='view',
                        comment=view_info.get('comment'),
                        metadata=view_info
                    )
                    
                    views[view_name] = view_schema
                    
        except Exception as e:
            logger.warning(f"Failed to get views info: {e}")
        
        return views
    
    async def _get_functions_info(self, connector) -> List[Dict[str, Any]]:
        """获取函数信息"""
        try:
            if hasattr(connector, 'get_functions'):
                return await connector.get_functions()
        except Exception as e:
            logger.warning(f"Failed to get functions info: {e}")
        
        return []
    
    async def _get_table_columns(self, connector, table_name: str) -> List[Dict[str, Any]]:
        """获取表列信息"""
        try:
            if hasattr(connector, 'get_table_columns'):
                return await connector.get_table_columns(table_name)
        except Exception as e:
            logger.warning(f"Failed to get columns for table {table_name}: {e}")
        
        return []
    
    async def _get_primary_keys(self, connector, table_name: str) -> List[str]:
        """获取主键信息"""
        try:
            if hasattr(connector, 'get_primary_keys'):
                return await connector.get_primary_keys(table_name)
        except Exception as e:
            logger.warning(f"Failed to get primary keys for table {table_name}: {e}")
        
        return []
    
    async def _get_foreign_keys(self, connector, table_name: str) -> List[Dict[str, str]]:
        """获取外键信息"""
        try:
            if hasattr(connector, 'get_foreign_keys'):
                return await connector.get_foreign_keys(table_name)
        except Exception as e:
            logger.warning(f"Failed to get foreign keys for table {table_name}: {e}")
        
        return []
    
    async def _get_indexes(self, connector, table_name: str) -> List[Dict[str, Any]]:
        """获取索引信息"""
        try:
            if hasattr(connector, 'get_indexes'):
                return await connector.get_indexes(table_name)
        except Exception as e:
            logger.warning(f"Failed to get indexes for table {table_name}: {e}")
        
        return []


class SchemaAnalysisService:
    """Schema分析服务"""
    
    def __init__(self):
        self.discovery_service = SchemaDiscoveryService()
    
    async def analyze_relationships(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """分析表关系"""
        relationships = {
            'foreign_key_relationships': [],
            'potential_relationships': [],
            'orphaned_tables': [],
            'relationship_graph': {}
        }
        
        # 分析外键关系
        for table_name, table in schema.tables.items():
            for fk in table.foreign_keys:
                relationships['foreign_key_relationships'].append({
                    'from_table': table_name,
                    'from_column': fk.get('column'),
                    'to_table': fk.get('referenced_table'),
                    'to_column': fk.get('referenced_column')
                })
        
        # 分析可能的关系（基于命名模式）
        relationships['potential_relationships'] = self._find_potential_relationships(schema)
        
        # 找出孤立表
        connected_tables = set()
        for rel in relationships['foreign_key_relationships']:
            connected_tables.add(rel['from_table'])
            connected_tables.add(rel['to_table'])
        
        all_tables = set(schema.tables.keys())
        relationships['orphaned_tables'] = list(all_tables - connected_tables)
        
        return relationships
    
    def _find_potential_relationships(self, schema: DatabaseSchema) -> List[Dict[str, str]]:
        """基于命名模式找出潜在关系"""
        potential = []
        
        # 简单的命名模式分析
        for table_name, table in schema.tables.items():
            for column in table.columns:
                column_name = column.get('name', '')
                
                # 查找可能的外键模式（如user_id指向users表的id）
                if column_name.endswith('_id'):
                    base_name = column_name[:-3]
                    
                    # 尝试找到对应的表
                    for target_table_name in schema.tables:
                        if (target_table_name.lower() == base_name.lower() or 
                            target_table_name.lower() == base_name.lower() + 's'):
                            
                            potential.append({
                                'from_table': table_name,
                                'from_column': column_name,
                                'to_table': target_table_name,
                                'to_column': 'id',
                                'confidence': 0.7
                            })
        
        return potential
    
    async def analyze_data_types(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """分析数据类型分布"""
        type_stats = {}
        column_count = 0
        
        for table in schema.tables.values():
            for column in table.columns:
                column_count += 1
                data_type = column.get('type', 'unknown').lower()
                
                if data_type not in type_stats:
                    type_stats[data_type] = 0
                type_stats[data_type] += 1
        
        # 计算百分比
        type_percentages = {
            dtype: (count / column_count) * 100 
            for dtype, count in type_stats.items()
        } if column_count > 0 else {}
        
        return {
            'total_columns': column_count,
            'type_counts': type_stats,
            'type_percentages': type_percentages
        }
    
    async def suggest_optimizations(self, schema: DatabaseSchema) -> List[Dict[str, Any]]:
        """建议优化"""
        suggestions = []
        
        for table_name, table in schema.tables.items():
            # 检查是否缺少主键
            if not table.primary_keys:
                suggestions.append({
                    'type': 'missing_primary_key',
                    'table': table_name,
                    'message': f'Table {table_name} lacks a primary key',
                    'priority': 'high'
                })
            
            # 检查大表是否缺少索引
            if len(table.columns) > 10 and len(table.indexes) == 0:
                suggestions.append({
                    'type': 'consider_indexing',
                    'table': table_name,
                    'message': f'Large table {table_name} might benefit from indexing',
                    'priority': 'medium'
                })
            
            # 检查命名规范
            if not table_name.islower():
                suggestions.append({
                    'type': 'naming_convention',
                    'table': table_name,
                    'message': f'Table name {table_name} should follow lowercase convention',
                    'priority': 'low'
                })
        
        return suggestions


# 全局schema服务实例
_global_schema_service = None

def get_schema_service() -> SchemaDiscoveryService:
    """获取全局schema服务"""
    global _global_schema_service
    if _global_schema_service is None:
        _global_schema_service = SchemaDiscoveryService()
    return _global_schema_service