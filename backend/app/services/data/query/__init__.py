"""
数据查询服务模块
"""

from .query_executor_service import query_executor_service, QueryExecutorService, QueryResult

__all__ = [
    'query_executor_service',
    'QueryExecutorService', 
    'QueryResult'
]