"""
数据查询优化器
支持Doris数据仓库的高性能查询优化
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from sqlalchemy import text, create_engine
import logging

from ...core.config import settings
from ...models.data_source import DataSource, DataSourceType


class QueryOptimizationStrategy(Enum):
    """查询优化策略"""
    PARTITION_PRUNING = "partition_pruning"      # 分区裁剪
    INDEX_OPTIMIZATION = "index_optimization"    # 索引优化  
    BATCH_PROCESSING = "batch_processing"        # 批量处理
    CACHE_UTILIZATION = "cache_utilization"      # 缓存利用
    VECTORIZATION = "vectorization"              # 向量化执行


@dataclass
class QueryPlan:
    """查询执行计划"""
    original_query: str
    optimized_query: str
    estimated_cost: float
    optimization_strategies: List[QueryOptimizationStrategy]
    partition_keys: List[str]
    index_hints: List[str]
    cache_key: Optional[str] = None


@dataclass
class QueryResult:
    """查询结果"""
    data: pd.DataFrame
    execution_time: float
    rows_scanned: int
    rows_returned: int
    cache_hit: bool
    optimization_applied: List[str]


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.query_cache = {}  # 简单内存缓存，生产环境应使用Redis
        
    async def optimize_and_execute(
        self, 
        data_source: DataSource,
        base_query: str,
        filters: Dict[str, Any],
        aggregations: List[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        优化并执行查询
        
        Args:
            data_source: 数据源信息
            base_query: 基础查询语句
            filters: 过滤条件
            aggregations: 聚合操作
            
        Returns:
            查询结果
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 生成查询计划
            query_plan = await self._generate_query_plan(
                data_source, base_query, filters, aggregations
            )
            
            # 检查缓存
            if query_plan.cache_key:
                cached_result = self._get_cached_result(query_plan.cache_key)
                if cached_result is not None:
                    return QueryResult(
                        data=cached_result,
                        execution_time=asyncio.get_event_loop().time() - start_time,
                        rows_scanned=0,
                        rows_returned=len(cached_result),
                        cache_hit=True,
                        optimization_applied=["cache_hit"]
                    )
            
            # 执行优化查询
            result_data, execution_stats = await self._execute_optimized_query(
                data_source, query_plan
            )
            
            # 缓存结果
            if query_plan.cache_key and len(result_data) > 0:
                self._cache_result(query_plan.cache_key, result_data)
            
            total_time = asyncio.get_event_loop().time() - start_time
            
            return QueryResult(
                data=result_data,
                execution_time=total_time,
                rows_scanned=execution_stats.get('rows_scanned', 0),
                rows_returned=len(result_data),
                cache_hit=False,
                optimization_applied=[s.value for s in query_plan.optimization_strategies]
            )
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise
    
    async def _generate_query_plan(
        self,
        data_source: DataSource,
        base_query: str,
        filters: Dict[str, Any],
        aggregations: List[Dict[str, Any]]
    ) -> QueryPlan:
        """生成查询执行计划"""
        
        optimization_strategies = []
        optimized_query = base_query
        partition_keys = []
        index_hints = []
        
        # 分析数据源类型
        if data_source.source_type == DataSourceType.sql:
            if self._is_doris_datasource(data_source):
                optimized_query, doris_strategies = await self._optimize_for_doris(
                    data_source, base_query, filters, aggregations
                )
                optimization_strategies.extend(doris_strategies)
            else:
                optimized_query, general_strategies = await self._optimize_for_general_sql(
                    data_source, base_query, filters, aggregations
                )
                optimization_strategies.extend(general_strategies)
        
        # 生成缓存键
        cache_key = self._generate_cache_key(optimized_query, filters, aggregations)
        
        # 估算查询成本
        estimated_cost = self._estimate_query_cost(optimized_query, filters)
        
        return QueryPlan(
            original_query=base_query,
            optimized_query=optimized_query,
            estimated_cost=estimated_cost,
            optimization_strategies=optimization_strategies,
            partition_keys=partition_keys,
            index_hints=index_hints,
            cache_key=cache_key
        )
    
    def _is_doris_datasource(self, data_source: DataSource) -> bool:
        """判断是否为Doris数据源"""
        connection_str = data_source.connection_string or ""
        return "doris" in connection_str.lower() or "8030" in connection_str
    
    async def _optimize_for_doris(
        self,
        data_source: DataSource,
        base_query: str,
        filters: Dict[str, Any],
        aggregations: List[Dict[str, Any]]
    ) -> Tuple[str, List[QueryOptimizationStrategy]]:
        """针对Doris的查询优化"""
        
        strategies = []
        optimized_query = base_query
        
        # 1. 分区裁剪优化
        if self._has_time_filter(filters):
            optimized_query = self._apply_partition_pruning(optimized_query, filters)
            strategies.append(QueryOptimizationStrategy.PARTITION_PRUNING)
        
        # 2. 向量化执行优化
        if aggregations:
            optimized_query = self._optimize_aggregations_for_doris(
                optimized_query, aggregations
            )
            strategies.append(QueryOptimizationStrategy.VECTORIZATION)
        
        # 3. 列式存储优化
        optimized_query = self._optimize_column_selection(optimized_query)
        strategies.append(QueryOptimizationStrategy.INDEX_OPTIMIZATION)
        
        return optimized_query, strategies
    
    async def _optimize_for_general_sql(
        self,
        data_source: DataSource,
        base_query: str,
        filters: Dict[str, Any],
        aggregations: List[Dict[str, Any]]
    ) -> Tuple[str, List[QueryOptimizationStrategy]]:
        """通用SQL优化"""
        
        strategies = []
        optimized_query = base_query
        
        # 添加LIMIT子句避免全表扫描
        if "LIMIT" not in optimized_query.upper():
            optimized_query += " LIMIT 10000"
            strategies.append(QueryOptimizationStrategy.BATCH_PROCESSING)
        
        # 优化WHERE条件顺序
        if filters:
            optimized_query = self._optimize_where_conditions(optimized_query, filters)
            strategies.append(QueryOptimizationStrategy.INDEX_OPTIMIZATION)
        
        return optimized_query, strategies
    
    def _has_time_filter(self, filters: Dict[str, Any]) -> bool:
        """检查是否有时间过滤条件"""
        time_fields = ['date', 'time', 'timestamp', 'created_at', 'updated_at']
        return any(field in str(filters).lower() for field in time_fields)
    
    def _apply_partition_pruning(self, query: str, filters: Dict[str, Any]) -> str:
        """应用分区裁剪"""
        # 为Doris添加分区裁剪提示
        if 'date' in filters or 'time' in filters:
            # 添加分区过滤提示
            hint = "/*+ USE_PARTITION_PRUNE */ "
            return hint + query
        return query
    
    def _optimize_aggregations_for_doris(
        self, 
        query: str, 
        aggregations: List[Dict[str, Any]]
    ) -> str:
        """优化Doris聚合查询"""
        # 添加向量化执行提示
        if aggregations:
            hint = "/*+ VECTORIZED_ENGINE */ "
            return hint + query
        return query
    
    def _optimize_column_selection(self, query: str) -> str:
        """优化列选择（避免SELECT *）"""
        if "SELECT *" in query.upper():
            self.logger.warning("Query uses SELECT *, consider specifying columns for better performance")
        return query
    
    def _optimize_where_conditions(self, query: str, filters: Dict[str, Any]) -> str:
        """优化WHERE条件顺序"""
        # 将选择性高的条件放在前面
        # 这里简化处理，实际应该根据统计信息优化
        return query
    
    def _generate_cache_key(
        self, 
        query: str, 
        filters: Dict[str, Any], 
        aggregations: List[Dict[str, Any]]
    ) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{query}:{filters}:{aggregations}"
        return f"query_cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _estimate_query_cost(self, query: str, filters: Dict[str, Any]) -> float:
        """估算查询成本"""
        base_cost = 1.0
        
        # 根据查询复杂度调整成本
        if "JOIN" in query.upper():
            base_cost *= 2.0
        if "GROUP BY" in query.upper():
            base_cost *= 1.5
        if not filters:
            base_cost *= 3.0  # 无过滤条件成本更高
            
        return base_cost
    
    async def _execute_optimized_query(
        self, 
        data_source: DataSource, 
        query_plan: QueryPlan
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """执行优化后的查询"""
        
        try:
            engine = create_engine(data_source.connection_string)
            
            # 记录执行统计
            execution_stats = {
                'rows_scanned': 0,
                'execution_time': 0
            }
            
            # 执行查询
            start_time = asyncio.get_event_loop().time()
            result_df = pd.read_sql(text(query_plan.optimized_query), engine)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            execution_stats['execution_time'] = execution_time
            execution_stats['rows_scanned'] = len(result_df)
            
            self.logger.info(
                f"Query executed successfully: {len(result_df)} rows in {execution_time:.3f}s"
            )
            
            return result_df, execution_stats
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise
    
    def _get_cached_result(self, cache_key: str) -> Optional[pd.DataFrame]:
        """获取缓存结果"""
        return self.query_cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, data: pd.DataFrame):
        """缓存查询结果"""
        # 简单的内存缓存，生产环境应该使用Redis或其他持久化缓存
        if len(self.query_cache) > 100:  # 限制缓存大小
            # 移除最旧的缓存项
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = data.copy()


# 创建全局优化器实例
query_optimizer = QueryOptimizer()