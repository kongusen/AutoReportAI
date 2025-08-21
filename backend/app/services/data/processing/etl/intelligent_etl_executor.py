"""
智能ETL执行器

执行AI生成的ETL指令，支持多种数据源和查询类型
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TypedDict

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.services.data.connectors.doris_connector import DorisConnector

logger = logging.getLogger(__name__)


class AggregationConfig(TypedDict):
    """聚合配置类型定义"""
    function: str  # sum, avg, count, max, min
    field: str


class TimeFilterConfig(TypedDict):
    """时间过滤配置类型定义"""
    field: str
    start_date: Optional[str]
    end_date: Optional[str]
    period: Optional[str]  # daily, weekly, monthly, yearly


class RegionFilterConfig(TypedDict):
    """区域过滤配置类型定义"""
    field: str
    regions: List[str]
    include_all: bool


class ProcessedData(TypedDict):
    """处理后的数据类型定义"""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    status: str
    error_message: Optional[str]


class ETLInstructions(TypedDict):
    """ETL指令类型定义"""
    query_type: str
    table_name: str
    fields: List[str] 
    filters: Optional[Dict[str, Any]]
    group_by: Optional[List[str]]
    order_by: Optional[List[str]]
    limit: Optional[int]


class IntelligentETLExecutor:
    """
    智能ETL执行器 - 执行AI生成的ETL指令
    支持多种数据源和查询类型
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.connectors = {}
        self.query_cache = {}
        
    def execute_instruction(
        self, 
        etl_instruction: Dict[str, Any], 
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        执行ETL指令
        
        Args:
            etl_instruction: AI生成的ETL指令
            data_source_id: 数据源ID
            
        Returns:
            查询结果字典
        """
        logger.info(f"开始执行ETL指令，数据源: {data_source_id}")
        start_time = time.time()
        
        try:
            # 获取数据源配置
            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                raise ValueError(f"数据源 {data_source_id} 不存在")
            
            # 验证ETL指令
            self._validate_etl_instruction(etl_instruction)
            
            # 根据数据源类型选择连接器
            connector = self._get_connector(data_source)
            
            # 执行查询
            query_result = self._execute_query(
                connector, 
                etl_instruction, 
                data_source
            )
            
            execution_time = time.time() - start_time
            
            logger.info(f"ETL指令执行完成，耗时: {execution_time:.2f}秒")
            
            return {
                "data": query_result,
                "metadata": {
                    "data_source_id": data_source_id,
                    "query_type": etl_instruction.get("query_type"),
                    "execution_time": execution_time,
                    "row_count": len(query_result) if isinstance(query_result, list) else 1,
                    "executed_at": datetime.utcnow().isoformat()
                },
                "etl_instruction": etl_instruction,
                "status": "success"
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"ETL指令执行失败: {str(e)}")
            
            return {
                "data": None,
                "metadata": {
                    "data_source_id": data_source_id,
                    "execution_time": execution_time,
                    "executed_at": datetime.utcnow().isoformat()
                },
                "etl_instruction": etl_instruction,
                "status": "error",
                "error": str(e)
            }
    
    def _validate_etl_instruction(self, etl_instruction: Dict[str, Any]):
        """验证ETL指令格式"""
        required_fields = ["query_type"]
        
        for field in required_fields:
            if field not in etl_instruction:
                raise ValueError(f"ETL指令缺少必要字段: {field}")
        
        query_type = etl_instruction.get("query_type")
        if query_type not in ["sql", "aggregation", "groupby"]:
            raise ValueError(f"不支持的查询类型: {query_type}")
    
    def _get_connector(self, data_source):
        """获取数据源连接器"""
        connector_key = f"{data_source.source_type}_{data_source.id}"
        
        if connector_key not in self.connectors:
            if data_source.source_type == "doris":
                self.connectors[connector_key] = DorisConnector.from_data_source(data_source)
            elif data_source.source_type in ["mysql", "postgresql"]:
                self.connectors[connector_key] = self._create_sql_connector(data_source)
            else:
                raise ValueError(f"不支持的数据源类型: {data_source.source_type}")
        
        return self.connectors[connector_key]
    
    def _create_sql_connector(self, data_source):
        """创建SQL数据库连接器"""
        # 这里可以根据需要实现不同的SQL连接器
        if data_source.source_type == "postgresql":
            connection_string = (
                f"postgresql://{data_source.username}:{data_source.password}"
                f"@{data_source.host}:{data_source.port}/{data_source.database}"
            )
        elif data_source.source_type == "mysql":
            connection_string = (
                f"mysql://{data_source.username}:{data_source.password}"
                f"@{data_source.host}:{data_source.port}/{data_source.database}"
            )
        else:
            raise ValueError(f"不支持的SQL数据源类型: {data_source.source_type}")
        
        return create_engine(connection_string)
    
    def _execute_query(
        self, 
        connector, 
        etl_instruction: Dict[str, Any], 
        data_source
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """执行具体查询"""
        query_type = etl_instruction.get("query_type")
        
        if query_type == "sql":
            return self._execute_sql_query(connector, etl_instruction, data_source)
        elif query_type == "aggregation":
            return self._execute_aggregation_query(connector, etl_instruction, data_source)
        elif query_type == "groupby":
            return self._execute_groupby_query(connector, etl_instruction, data_source)
        else:
            raise ValueError(f"不支持的查询类型: {query_type}")
    
    def _execute_sql_query(
        self, 
        connector, 
        etl_instruction: Dict[str, Any], 
        data_source
    ) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        sql_query = etl_instruction.get("sql_query")
        if not sql_query:
            raise ValueError("SQL查询语句为空")
        
        try:
            if data_source.source_type == "doris":
                # 使用Doris连接器
                results = connector.execute_query(sql_query)
                return results
            else:
                # 使用SQLAlchemy引擎
                with connector.connect() as connection:
                    result = connection.execute(text(sql_query))
                    columns = result.keys()
                    rows = result.fetchall()
                    
                    # 转换为字典列表
                    return [dict(zip(columns, row)) for row in rows]
                    
        except Exception as e:
            logger.error(f"SQL查询执行失败: {str(e)}")
            raise
    
    def _execute_aggregation_query(
        self, 
        connector, 
        etl_instruction: Dict[str, Any], 
        data_source
    ) -> Dict[str, Any]:
        """执行聚合查询"""
        aggregation = etl_instruction.get("aggregation", "count")
        table_name = etl_instruction.get("table", "your_table")
        column = etl_instruction.get("column", "*")
        filters = etl_instruction.get("filters", [])
        
        # 构建聚合SQL
        if aggregation.upper() == "COUNT":
            sql = f"SELECT COUNT(*) as result FROM {table_name}"
        elif aggregation.upper() in ["SUM", "AVG", "MAX", "MIN"]:
            if column == "*":
                raise ValueError(f"{aggregation}聚合需要指定列名")
            sql = f"SELECT {aggregation.upper()}({column}) as result FROM {table_name}"
        else:
            raise ValueError(f"不支持的聚合类型: {aggregation}")
        
        # 添加过滤条件
        if filters:
            where_clauses = []
            for filter_item in filters:
                field = filter_item.get("field")
                operator = filter_item.get("operator", "=")
                value = filter_item.get("value")
                
                if isinstance(value, str):
                    where_clauses.append(f"{field} {operator} '{value}'")
                else:
                    where_clauses.append(f"{field} {operator} {value}")
            
            if where_clauses:
                sql += f" WHERE {' AND '.join(where_clauses)}"
        
        logger.info(f"执行聚合查询: {sql}")
        
        # 执行查询
        result = self._execute_sql_query(
            connector, 
            {"sql_query": sql}, 
            data_source
        )
        
        if result:
            return {"aggregation_result": result[0].get("result", 0)}
        else:
            return {"aggregation_result": 0}
    
    def _execute_groupby_query(
        self, 
        connector, 
        etl_instruction: Dict[str, Any], 
        data_source
    ) -> List[Dict[str, Any]]:
        """执行分组查询"""
        group_by = etl_instruction.get("group_by", [])
        aggregation = etl_instruction.get("aggregation", "count")
        table_name = etl_instruction.get("table", "your_table")
        column = etl_instruction.get("column", "*")
        order_by = etl_instruction.get("order_by", {})
        limit = etl_instruction.get("limit")
        
        if not group_by:
            raise ValueError("分组查询必须指定group_by字段")
        
        # 构建SELECT子句
        select_fields = group_by.copy()
        
        if aggregation.upper() == "COUNT":
            select_fields.append("COUNT(*) as count")
        elif aggregation.upper() in ["SUM", "AVG", "MAX", "MIN"]:
            if column == "*":
                raise ValueError(f"{aggregation}聚合需要指定列名")
            select_fields.append(f"{aggregation.upper()}({column}) as {aggregation.lower()}_result")
        
        # 构建SQL
        sql = f"SELECT {', '.join(select_fields)} FROM {table_name}"
        sql += f" GROUP BY {', '.join(group_by)}"
        
        # 添加排序
        if order_by.get("field"):
            direction = order_by.get("direction", "asc").upper()
            sql += f" ORDER BY {order_by['field']} {direction}"
        
        # 添加限制
        if limit:
            sql += f" LIMIT {limit}"
        
        logger.info(f"执行分组查询: {sql}")
        
        # 执行查询
        return self._execute_sql_query(
            connector, 
            {"sql_query": sql}, 
            data_source
        )
    
    def get_table_schema(self, data_source_id: str, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        try:
            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                raise ValueError(f"数据源 {data_source_id} 不存在")
            
            connector = self._get_connector(data_source)
            
            if data_source.source_type == "doris":
                # Doris获取表结构
                schema_query = f"DESCRIBE {table_name}"
                schema_result = connector.execute_query(schema_query)
                
                return {
                    "table_name": table_name,
                    "columns": schema_result,
                    "data_source_type": data_source.source_type
                }
            else:
                # SQL数据库获取表结构
                schema_query = f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                """
                
                with connector.connect() as connection:
                    result = connection.execute(text(schema_query))
                    columns = [dict(row._mapping) for row in result.fetchall()]
                
                return {
                    "table_name": table_name,
                    "columns": columns,
                    "data_source_type": data_source.source_type
                }
                
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            raise
    
    def list_tables(self, data_source_id: str) -> List[str]:
        """列出数据源中的所有表"""
        try:
            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                raise ValueError(f"数据源 {data_source_id} 不存在")
            
            connector = self._get_connector(data_source)
            
            if data_source.source_type == "doris":
                # Doris列出表
                tables_query = "SHOW TABLES"
                tables_result = connector.execute_query(tables_query)
                return [table_info.get("Tables_in_" + data_source.doris_database, "") 
                       for table_info in tables_result]
            else:
                # SQL数据库列出表
                tables_query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """
                
                with connector.connect() as connection:
                    result = connection.execute(text(tables_query))
                    return [row[0] for row in result.fetchall()]
                    
        except Exception as e:
            logger.error(f"列出表失败: {str(e)}")
            raise
    
    def test_connection(self, data_source_id: str) -> Dict[str, Any]:
        """测试数据源连接"""
        try:
            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                return {"status": "error", "message": f"数据源 {data_source_id} 不存在"}
            
            connector = self._get_connector(data_source)
            
            # 执行简单测试查询
            if data_source.source_type == "doris":
                test_result = connector.execute_query("SELECT 1 as test")
            else:
                with connector.connect() as connection:
                    result = connection.execute(text("SELECT 1 as test"))
                    test_result = [dict(row._mapping) for row in result.fetchall()]
            
            return {
                "status": "success",
                "message": "连接测试成功",
                "data_source_type": data_source.source_type,
                "test_result": test_result
            }
            
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return {
                "status": "error", 
                "message": f"连接测试失败: {str(e)}"
            }


# 全局实例
intelligent_etl_executor = None