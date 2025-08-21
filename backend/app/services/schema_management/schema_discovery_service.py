"""
表结构发现服务
负责从数据源发现表结构信息并存储到数据库
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.data_source import DataSource
from app.models.table_schema import TableSchema, ColumnSchema
from app.services.connectors.doris_connector import create_doris_connector
from .utils.type_normalizer import TypeNormalizer


class SchemaDiscoveryService:
    """表结构发现服务"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.type_normalizer = TypeNormalizer()
    
    async def discover_and_store_schemas(self, data_source_id: str) -> Dict[str, Any]:
        """
        发现并存储数据源的所有表结构
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            发现结果
        """
        try:
            # 获取数据源
            data_source = self.db_session.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                return {"success": False, "error": "数据源不存在"}
            
            # 根据数据源类型选择连接器
            if data_source.source_type.value == "doris":
                return await self._discover_doris_schemas(data_source)
            else:
                return {"success": False, "error": f"不支持的数据源类型: {data_source.source_type.value}"}
                
        except Exception as e:
            self.logger.error(f"发现表结构失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _discover_doris_schemas(self, data_source: DataSource) -> Dict[str, Any]:
        """发现Doris数据源的表结构"""
        
        try:
            # 创建Doris连接器
            connector = create_doris_connector(data_source)
            
            async with connector:
                # 测试连接
                connection_test = await connector.test_connection()
                if not connection_test.get("success"):
                    return {"success": False, "error": f"连接失败: {connection_test.get('error')}"}
                
                # 获取所有表
                tables = await connector.get_all_tables()
                if not tables:
                    return {"success": False, "error": "未发现任何表"}
                
                # 存储表结构信息
                stored_tables = []
                for table_name in tables:
                    try:
                        # 获取表结构
                        schema_info = await connector.get_table_schema(table_name)
                        if "error" not in schema_info:
                            # 存储表结构
                            table_schema = await self._store_table_schema(
                                data_source, table_name, schema_info
                            )
                            stored_tables.append(table_schema)
                            
                            # 获取表统计信息
                            stats_info = await connector.get_table_statistics(table_name)
                            if "error" not in stats_info:
                                await self._update_table_statistics(table_schema, stats_info)
                                
                    except Exception as e:
                        self.logger.warning(f"处理表 {table_name} 时出错: {e}")
                        # 回滚当前事务
                        self.db_session.rollback()
                        continue
                
                return {
                    "success": True,
                    "message": f"成功发现并存储 {len(stored_tables)} 个表的结构信息",
                    "tables_count": len(stored_tables),
                    "tables": [table.table_name for table in stored_tables]
                }
                
        except Exception as e:
            self.logger.error(f"发现Doris表结构失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_table_schema(
        self, 
        data_source: DataSource, 
        table_name: str, 
        schema_info: Dict[str, Any]
    ) -> TableSchema:
        """存储表结构信息"""
        
        # 检查是否已存在
        existing_schema = self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source.id,
                TableSchema.table_name == table_name
            )
        ).first()
        
        if existing_schema:
            # 更新现有记录
            existing_schema.columns_info = schema_info.get("columns", [])
            existing_schema.updated_at = datetime.utcnow()
            table_schema = existing_schema
        else:
            # 创建新记录
            table_schema = TableSchema(
                data_source_id=data_source.id,
                table_name=table_name,
                columns_info=schema_info.get("columns", []),
                is_active=True,
                is_analyzed=False
            )
            self.db_session.add(table_schema)
        
        # 先提交表结构，确保有ID
        self.db_session.commit()
        
        # 存储列信息
        await self._store_column_schemas(table_schema, schema_info.get("columns", []))
        
        # 再次提交列信息
        self.db_session.commit()
        return table_schema
    
    async def _store_column_schemas(
        self, 
        table_schema: TableSchema, 
        columns_info: List[Dict[str, Any]]
    ):
        """存储列结构信息"""
        
        for col_info in columns_info:
            # 检查列是否已存在
            existing_column = self.db_session.query(ColumnSchema).filter(
                and_(
                    ColumnSchema.table_schema_id == table_schema.id,
                    ColumnSchema.column_name == col_info.get("name")
                )
            ).first()
            
            # 标准化数据类型
            normalized_type = self.type_normalizer.normalize_type(col_info.get("type", ""))
            
            column_data = {
                "column_name": col_info.get("name"),
                "column_type": col_info.get("type", ""),
                "normalized_type": normalized_type.value if hasattr(normalized_type, 'value') else str(normalized_type),  # 兼容字符串和枚举
                "is_nullable": col_info.get("nullable", True),
                "is_primary_key": col_info.get("key", "") == "PRI",
                "default_value": col_info.get("default"),
                "column_size": self.type_normalizer.extract_column_size(col_info.get("type", "")),
                "precision": self.type_normalizer.extract_precision(col_info.get("type", "")),
                "scale": self.type_normalizer.extract_scale(col_info.get("type", ""))
            }
            
            if existing_column:
                # 更新现有列
                for key, value in column_data.items():
                    setattr(existing_column, key, value)
                existing_column.updated_at = datetime.utcnow()
            else:
                # 创建新列
                column_schema = ColumnSchema(
                    table_schema_id=table_schema.id,
                    **column_data
                )
                self.db_session.add(column_schema)
    
    async def _update_table_statistics(
        self, 
        table_schema: TableSchema, 
        stats_info: Dict[str, Any]
    ):
        """更新表统计信息"""
        
        # 转换numpy类型为Python原生类型
        rows = stats_info.get("rows")
        data_length = stats_info.get("data_length")
        
        table_schema.estimated_row_count = int(rows) if rows is not None else None
        table_schema.table_size_bytes = int(data_length) if data_length is not None else None
        table_schema.last_analyzed = datetime.utcnow()
        
        self.db_session.commit()
    
    async def refresh_schema(self, data_source_id: str) -> Dict[str, Any]:
        """
        刷新数据源的表结构信息
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            刷新结果
        """
        try:
            # 先删除现有的表结构信息
            self.db_session.query(TableSchema).filter(
                TableSchema.data_source_id == data_source_id
            ).delete()
            
            self.db_session.commit()
            
            # 重新发现表结构
            return await self.discover_and_store_schemas(data_source_id)
            
        except Exception as e:
            self.logger.error(f"刷新表结构失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_discovery_status(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取表结构发现状态
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            发现状态信息
        """
        try:
            table_count = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).count()
            
            analyzed_count = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True,
                    TableSchema.is_analyzed == True
                )
            ).count()
            
            return {
                "success": True,
                "total_tables": table_count,
                "analyzed_tables": analyzed_count,
                "discovery_complete": table_count > 0
            }
            
        except Exception as e:
            self.logger.error(f"获取发现状态失败: {e}")
            return {"success": False, "error": str(e)}
