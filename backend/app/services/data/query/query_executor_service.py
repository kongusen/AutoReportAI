"""
数据查询执行器服务

负责执行各种数据查询操作，支持多种数据源类型
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time: float
    error: Optional[str] = None


class QueryExecutorService:
    """数据查询执行器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sql_replacer = SqlPlaceholderReplacer()

    async def execute_query_with_placeholders(
        self,
        sql_query: str,
        time_context: Dict[str, Any],
        connection_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行包含占位符的SQL查询

        Args:
            sql_query: 包含占位符的SQL (如: "WHERE dt BETWEEN {{start_date}} AND {{end_date}}")
            time_context: 时间上下文，用于替换占位符
            connection_params: 连接参数

        Returns:
            查询结果字典
        """
        try:
            # 替换SQL中的占位符
            resolved_sql = self.sql_replacer.replace_time_placeholders(sql_query, time_context)

            # 记录占位符替换信息
            placeholders = self.sql_replacer.extract_placeholders(sql_query)
            if placeholders:
                self.logger.info(f"替换了 {len(placeholders)} 个占位符: {placeholders}")
                self.logger.debug(f"原始SQL: {sql_query}")
                self.logger.debug(f"替换后SQL: {resolved_sql}")

            # 执行替换后的SQL
            return await self.execute_query(resolved_sql, connection_params)

        except Exception as e:
            self.logger.error(f"执行占位符SQL查询失败: {e}")
            return {
                "success": False,
                "data": [],
                "metadata": {
                    "error": f"占位符SQL执行失败: {str(e)}",
                    "original_sql": sql_query,
                    "time_context": time_context
                },
                "execution_time": 0.0,
                "error": str(e)
            }

    async def execute_query(
        self,
        sql_query: str,
        connection_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行SQL查询
        
        Args:
            sql_query: SQL查询语句
            connection_params: 连接参数，如果为None则使用默认数据源
            
        Returns:
            查询结果字典
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"执行SQL查询: {sql_query[:100]}...")
            
            # 验证SQL查询安全性
            if not self._validate_sql_safety(sql_query):
                raise ValueError("SQL查询包含不安全的操作")
            
            # 获取数据源连接
            connector = await self._get_connector(connection_params)
            
            try:
                # 执行查询
                result = await connector.execute_query(sql_query)
                execution_time = time.time() - start_time
                
                if hasattr(result, 'data') and not result.data.empty:
                    data_records = result.data.to_dict('records')
                    columns = result.data.columns.tolist()
                    
                    return {
                        "success": True,
                        "data": data_records,
                        "metadata": {
                            "columns": columns,
                            "row_count": len(data_records),
                            "query": sql_query,
                            "execution_time": execution_time,
                            "data_source": getattr(connector, 'data_source_name', 'unknown')
                        },
                        "execution_time": execution_time
                    }
                else:
                    return {
                        "success": True,
                        "data": [],
                        "metadata": {
                            "columns": [],
                            "row_count": 0,
                            "query": sql_query,
                            "execution_time": execution_time,
                            "message": "查询成功但无数据返回"
                        },
                        "execution_time": execution_time
                    }
                    
            finally:
                await connector.disconnect()
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"查询执行失败: {e}")
            
            return {
                "success": False,
                "data": [],
                "metadata": {
                    "query": sql_query,
                    "execution_time": execution_time,
                    "error": str(e)
                },
                "execution_time": execution_time,
                "error": str(e)
            }
    
    def _validate_sql_safety(self, sql_query: str) -> bool:
        """验证SQL查询安全性"""
        sql_upper = sql_query.upper().strip()
        
        # 只允许SELECT查询
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 禁止的操作
        forbidden_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 
            'CREATE', 'TRUNCATE', 'EXECUTE', 'EXEC'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return False
                
        return True
    
    async def _get_connector(self, connection_params: Optional[Dict] = None):
        """获取数据连接器"""
        if connection_params and 'data_source_id' in connection_params:
            # 使用指定的数据源
            from app.services.data.connectors.connector_factory import create_connector
            from app.crud.crud_data_source import crud_data_source
            from app.db.session import get_db_session
            
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=connection_params['data_source_id'])
                if not data_source:
                    raise ValueError(f"数据源不存在: {connection_params['data_source_id']}")
                
                connector = create_connector(data_source)
                await connector.connect()
                return connector
        else:
            # 使用默认数据源
            from app.services.data.sources.data_source_service import data_source_service
            default_connector = await data_source_service.get_default_connector()
            if not default_connector:
                raise ValueError("没有可用的默认数据源")
            
            return default_connector
    
    async def execute_batch_queries(
        self, 
        queries: List[str], 
        connection_params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        批量执行查询
        
        Args:
            queries: SQL查询列表
            connection_params: 连接参数
            
        Returns:
            查询结果列表
        """
        results = []
        
        # 并发执行查询（如果安全）
        if len(queries) <= 5:  # 限制并发数量
            tasks = [
                self.execute_query(query, connection_params) 
                for query in queries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    results[i] = {
                        "success": False,
                        "data": [],
                        "metadata": {"query": queries[i]},
                        "execution_time": 0,
                        "error": str(result)
                    }
        else:
            # 串行执行
            for query in queries:
                result = await self.execute_query(query, connection_params)
                results.append(result)
        
        return results


# 全局实例
query_executor_service = QueryExecutorService()