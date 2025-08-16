"""
元数据发现服务 - 智能发现和管理多库多表结构
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.data_source import DataSource, DataSourceType
from app.models.table_schema import Database, Table, TableColumn, TableRelation, RelationType
from app.services.connectors.connector_factory import create_connector


@dataclass
class DiscoveryResult:
    """发现结果"""
    success: bool
    databases_found: int = 0
    tables_found: int = 0
    columns_found: int = 0
    relations_found: int = 0
    errors: List[str] = None
    discovery_time: float = 0.0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass  
class TableMetadata:
    """表元数据"""
    name: str
    schema: str
    table_type: str = "table"
    row_count: int = 0
    size_mb: float = 0.0
    engine: str = None
    charset: str = None
    comment: str = None
    columns: List[Dict] = None
    indexes: List[Dict] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []
        if self.indexes is None:
            self.indexes = []


class MetadataDiscoveryService:
    """元数据发现服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def discover_data_source_metadata(
        self, 
        data_source_id: str,
        full_discovery: bool = False
    ) -> DiscoveryResult:
        """
        发现数据源的完整元数据
        
        Args:
            data_source_id: 数据源ID
            full_discovery: 是否进行完整发现（包括统计信息）
            
        Returns:
            发现结果
        """
        start_time = datetime.now()
        result = DiscoveryResult(success=False)
        
        try:
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    result.errors.append(f"Data source {data_source_id} not found")
                    return result
                
                self.logger.info(f"Starting metadata discovery for data source: {data_source.name}")
                
                # 创建连接器
                connector = create_connector(data_source)
                
                async with connector:
                    # 1. 发现数据库
                    databases = await self._discover_databases(connector, data_source, db)
                    result.databases_found = len(databases)
                    
                    # 2. 发现每个数据库中的表
                    total_tables = 0
                    total_columns = 0
                    
                    for database in databases:
                        tables = await self._discover_tables(connector, database, db, full_discovery)
                        total_tables += len(tables)
                        
                        # 3. 发现表中的字段
                        for table in tables:
                            columns = await self._discover_columns(connector, table, db)
                            total_columns += len(columns)
                    
                    result.tables_found = total_tables
                    result.columns_found = total_columns
                    
                    # 4. 推理表间关系（可选）
                    if full_discovery:
                        relations = await self._infer_table_relations(data_source_id, db)
                        result.relations_found = len(relations)
                
                result.success = True
                self.logger.info(f"Metadata discovery completed: {result}")
                
        except Exception as e:
            self.logger.error(f"Error during metadata discovery: {e}")
            result.errors.append(str(e))
            
        finally:
            result.discovery_time = (datetime.now() - start_time).total_seconds()
            
        return result
    
    async def _discover_databases(
        self, 
        connector, 
        data_source: DataSource,
        db: Session
    ) -> List[Database]:
        """发现数据库列表"""
        databases = []
        
        try:
            # 对于Doris，获取所有数据库
            if data_source.source_type == DataSourceType.doris:
                database_list = await self._get_doris_databases(connector)
            else:
                # 其他数据源类型的处理
                database_list = [data_source.doris_database or "default"]
            
            for db_name in database_list:
                # 检查数据库是否已存在
                existing_db = db.query(Database).filter(
                    Database.data_source_id == data_source.id,
                    Database.name == db_name
                ).first()
                
                if not existing_db:
                    # 创建新数据库记录
                    new_db = Database(
                        name=db_name,
                        display_name=db_name.title(),
                        data_source_id=data_source.id,
                        is_active=True
                    )
                    db.add(new_db)
                    db.flush()  # 获取ID
                    databases.append(new_db)
                    self.logger.info(f"Discovered new database: {db_name}")
                else:
                    databases.append(existing_db)
                    
        except Exception as e:
            self.logger.error(f"Error discovering databases: {e}")
            raise
            
        return databases
    
    async def _discover_tables(
        self,
        connector,
        database: Database,
        db: Session,
        full_discovery: bool = False
    ) -> List[Table]:
        """发现数据库中的表"""
        tables = []
        
        try:
            # 获取表列表
            table_metadata_list = await self._get_database_tables(connector, database.name)
            
            for table_meta in table_metadata_list:
                # 检查表是否已存在
                existing_table = db.query(Table).filter(
                    Table.database_id == database.id,
                    Table.name == table_meta.name
                ).first()
                
                if not existing_table:
                    # 创建新表记录
                    new_table = Table(
                        name=table_meta.name,
                        display_name=table_meta.name.replace("_", " ").title(),
                        database_id=database.id,
                        table_type=table_meta.table_type,
                        engine=table_meta.engine,
                        charset=table_meta.charset,
                        row_count=table_meta.row_count if full_discovery else 0,
                        size_mb=table_meta.size_mb if full_discovery else 0.0,
                        is_active=True
                    )
                    db.add(new_table)
                    db.flush()
                    tables.append(new_table)
                    self.logger.info(f"Discovered new table: {database.name}.{table_meta.name}")
                else:
                    # 更新统计信息
                    if full_discovery:
                        existing_table.row_count = table_meta.row_count
                        existing_table.size_mb = table_meta.size_mb
                        existing_table.last_analyzed = datetime.utcnow()
                    tables.append(existing_table)
                    
        except Exception as e:
            self.logger.error(f"Error discovering tables for database {database.name}: {e}")
            raise
            
        return tables
    
    async def _discover_columns(
        self,
        connector,
        table: Table,
        db: Session
    ) -> List[TableColumn]:
        """发现表中的字段"""
        columns = []
        
        try:
            # 获取表结构
            column_info_list = await self._get_table_columns(connector, table.database.name, table.name)
            
            for i, col_info in enumerate(column_info_list):
                # 检查字段是否已存在
                existing_column = db.query(TableColumn).filter(
                    TableColumn.table_id == table.id,
                    TableColumn.name == col_info['name']
                ).first()
                
                if not existing_column:
                    # 创建新字段记录
                    new_column = TableColumn(
                        name=col_info['name'],
                        display_name=col_info.get('comment') or col_info['name'].replace("_", " ").title(),
                        table_id=table.id,
                        data_type=self._normalize_column_type(col_info['type']),
                        raw_type=col_info['type'],
                        max_length=col_info.get('length'),
                        precision=col_info.get('precision'),
                        scale=col_info.get('scale'),
                        is_nullable=col_info.get('nullable', True),
                        is_primary_key=col_info.get('primary_key', False),
                        is_unique=col_info.get('unique', False),
                        default_value=col_info.get('default'),
                        column_comment=col_info.get('comment'),
                        ordinal_position=i + 1
                    )
                    db.add(new_column)
                    columns.append(new_column)
                    
                else:
                    columns.append(existing_column)
                    
        except Exception as e:
            self.logger.error(f"Error discovering columns for table {table.name}: {e}")
            raise
            
        return columns
    
    async def _infer_table_relations(
        self,
        data_source_id: str,
        db: Session
    ) -> List[TableRelation]:
        """推理表间关系"""
        relations = []
        
        try:
            # 获取数据源下的所有表
            tables = db.query(Table).join(Database).filter(
                Database.data_source_id == data_source_id
            ).all()
            
            # 基于命名约定推理关系
            for table in tables:
                table_relations = await self._infer_table_relationships_by_naming(table, tables, db)
                relations.extend(table_relations)
                
            # 基于外键约束推理关系（如果数据库支持）
            # TODO: 实现外键约束发现
            
        except Exception as e:
            self.logger.error(f"Error inferring table relations: {e}")
            
        return relations
    
    async def _infer_table_relationships_by_naming(
        self,
        table: Table,
        all_tables: List[Table],
        db: Session
    ) -> List[TableRelation]:
        """基于命名约定推理表关系"""
        relations = []
        
        try:
            # 获取表的所有字段
            columns = db.query(TableColumn).filter(TableColumn.table_id == table.id).all()
            
            for column in columns:
                # 检查是否为外键字段（通常以_id结尾）
                if column.name.endswith('_id') and column.name != 'id':
                    # 推测关联的表名
                    potential_table_name = column.name[:-3]  # 移除_id后缀
                    
                    # 查找可能的关联表
                    for target_table in all_tables:
                        if target_table.id == table.id:
                            continue
                            
                        # 名称匹配或包含关系
                        if (target_table.name == potential_table_name or
                            potential_table_name in target_table.name or
                            target_table.name in potential_table_name):
                            
                            # 检查关系是否已存在
                            existing_relation = db.query(TableRelation).filter(
                                TableRelation.parent_table_id == target_table.id,
                                TableRelation.child_table_id == table.id
                            ).first()
                            
                            if not existing_relation:
                                # 创建新关系
                                relation = TableRelation(
                                    name=f"{target_table.name}_{table.name}_relation",
                                    parent_table_id=target_table.id,
                                    child_table_id=table.id,
                                    relation_type=RelationType.ONE_TO_MANY,
                                    parent_columns=[column.name.replace('_id', '') + '.id'],
                                    child_columns=[column.name],
                                    confidence_score=0.7,  # 基于命名推理的置信度
                                    business_meaning=f"{target_table.name} has many {table.name}",
                                    is_validated=False
                                )
                                db.add(relation)
                                relations.append(relation)
                                
        except Exception as e:
            self.logger.error(f"Error inferring relationships for table {table.name}: {e}")
            
        return relations
    
    # 数据源特定的方法
    async def _get_doris_databases(self, connector) -> List[str]:
        """获取Doris数据库列表"""
        try:
            # 执行SHOW DATABASES查询
            query = "SHOW DATABASES"
            result = await connector.execute_query(query)
            return [row[0] for row in result.data.values.tolist()]
        except Exception as e:
            self.logger.error(f"Error getting Doris databases: {e}")
            return []
    
    async def _get_database_tables(self, connector, database_name: str) -> List[TableMetadata]:
        """获取数据库中的表信息"""
        try:
            # 使用数据库
            await connector.execute_query(f"USE {database_name}")
            
            # 获取表列表
            query = "SHOW TABLES"
            result = await connector.execute_query(query)
            
            tables = []
            for row in result.data.values.tolist():
                table_name = row[0]
                
                # 获取表的详细信息
                table_info = TableMetadata(
                    name=table_name,
                    schema=database_name,
                    table_type="table"
                )
                
                # 可以进一步获取表的统计信息
                # TODO: 实现表统计信息获取
                
                tables.append(table_info)
                
            return tables
            
        except Exception as e:
            self.logger.error(f"Error getting tables for database {database_name}: {e}")
            return []
    
    async def _get_table_columns(self, connector, database_name: str, table_name: str) -> List[Dict]:
        """获取表的字段信息"""
        try:
            # 使用DESCRIBE或SHOW COLUMNS获取表结构
            query = f"DESCRIBE {database_name}.{table_name}"
            result = await connector.execute_query(query)
            
            columns = []
            for row in result.data.values.tolist():
                # 解析字段信息（根据Doris的DESCRIBE输出格式）
                column_info = {
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'Yes',
                    'primary_key': row[3] == 'PRI' if len(row) > 3 else False,
                    'default': row[4] if len(row) > 4 else None,
                    'comment': row[5] if len(row) > 5 else None
                }
                columns.append(column_info)
                
            return columns
            
        except Exception as e:
            self.logger.error(f"Error getting columns for table {database_name}.{table_name}: {e}")
            return []
    
    def _normalize_column_type(self, raw_type: str) -> str:
        """标准化字段类型"""
        raw_type = raw_type.lower()
        
        if 'int' in raw_type:
            if 'bigint' in raw_type:
                return 'BIGINT'
            return 'INTEGER'
        elif 'varchar' in raw_type or 'char' in raw_type:
            return 'STRING'
        elif 'text' in raw_type:
            return 'TEXT'
        elif 'decimal' in raw_type or 'numeric' in raw_type:
            return 'DECIMAL'
        elif 'float' in raw_type or 'double' in raw_type:
            return 'FLOAT'
        elif 'date' in raw_type:
            if 'datetime' in raw_type:
                return 'DATETIME'
            return 'DATE'
        elif 'timestamp' in raw_type:
            return 'TIMESTAMP'
        elif 'boolean' in raw_type or 'bool' in raw_type:
            return 'BOOLEAN'
        elif 'json' in raw_type:
            return 'JSON'
        else:
            return 'STRING'  # 默认类型