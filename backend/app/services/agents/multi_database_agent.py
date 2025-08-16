"""
多库多表智能Agent - 为Agent提供统一的多库多表访问能力
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.services.data_discovery.metadata_discovery_service import MetadataDiscoveryService, DiscoveryResult
from app.services.data_discovery.intelligent_query_router import IntelligentQueryRouter, QueryPlan
from app.services.data_discovery.cross_database_executor import CrossDatabaseExecutor, ExecutionResult


@dataclass
class AgentQueryRequest:
    """Agent查询请求"""
    query: str  # 自然语言查询
    data_source_id: str  # 数据源ID
    context: Optional[Dict[str, Any]] = None  # 上下文信息
    max_rows: Optional[int] = 1000  # 最大返回行数
    timeout: Optional[int] = 300  # 超时时间（秒）


@dataclass
class AgentQueryResponse:
    """Agent查询响应"""
    success: bool
    data: Optional[Any] = None  # 查询结果数据
    explanation: str = ""  # 查询解释
    sql_queries: List[str] = None  # 执行的SQL查询
    metadata: Dict[str, Any] = None  # 元数据信息
    performance_stats: Dict[str, Any] = None  # 性能统计
    errors: List[str] = None  # 错误信息
    
    def __post_init__(self):
        if self.sql_queries is None:
            self.sql_queries = []
        if self.metadata is None:
            self.metadata = {}
        if self.performance_stats is None:
            self.performance_stats = {}
        if self.errors is None:
            self.errors = []


class MultiDatabaseAgent:
    """多库多表智能Agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metadata_service = MetadataDiscoveryService()
        self.query_router = IntelligentQueryRouter()
        self.executor = CrossDatabaseExecutor()
        
        # 缓存已发现的元数据
        self._metadata_cache = {}
        self._cache_ttl = 3600  # 1小时缓存
    
    async def query(self, request: AgentQueryRequest) -> AgentQueryResponse:
        """
        执行智能查询
        
        这是Agent访问多库多表数据的主要入口点
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Agent query: {request.query}")
            
            # 1. 确保元数据已发现
            await self._ensure_metadata_discovered(request.data_source_id)
            
            # 2. 智能查询路由
            query_plan = await self.query_router.route_query(
                request.query,
                request.data_source_id,
                request.context
            )
            
            # 3. 执行查询计划
            execution_result = await self.executor.execute_query_plan(
                query_plan,
                request.data_source_id
            )
            
            # 4. 构建响应
            response = await self._build_response(
                request,
                query_plan,
                execution_result,
                start_time
            )
            
            self.logger.info(f"Agent query completed: success={response.success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in agent query: {e}")
            return AgentQueryResponse(
                success=False,
                explanation=f"查询执行失败: {str(e)}",
                errors=[str(e)],
                performance_stats={
                    'total_time': (datetime.now() - start_time).total_seconds()
                }
            )
    
    async def discover_schema(self, data_source_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        发现数据源的数据库模式
        
        Args:
            data_source_id: 数据源ID
            force_refresh: 是否强制刷新元数据
            
        Returns:
            数据库模式信息
        """
        try:
            # 检查缓存
            cache_key = f"schema_{data_source_id}"
            if not force_refresh and cache_key in self._metadata_cache:
                cached_data, cached_time = self._metadata_cache[cache_key]
                if (datetime.now() - cached_time).seconds < self._cache_ttl:
                    return cached_data
            
            # 执行元数据发现
            discovery_result = await self.metadata_service.discover_data_source_metadata(
                data_source_id,
                full_discovery=True
            )
            
            schema_info = {
                'data_source_id': data_source_id,
                'databases': discovery_result.databases_found,
                'tables': discovery_result.tables_found,
                'columns': discovery_result.columns_found,
                'relations': discovery_result.relations_found,
                'discovery_time': discovery_result.discovery_time,
                'last_updated': datetime.now().isoformat()
            }
            
            # 更新缓存
            self._metadata_cache[cache_key] = (schema_info, datetime.now())
            
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Error discovering schema: {e}")
            raise
    
    async def get_available_tables(self, data_source_id: str, business_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取可用的表列表
        
        Args:
            data_source_id: 数据源ID
            business_domain: 业务域过滤（可选）
            
        Returns:
            表信息列表
        """
        try:
            from sqlalchemy.orm import Session
            from app.db.session import get_db_session
            from app.models.table_schema import Database, Table
            
            with get_db_session() as db:
                query = db.query(Table).join(Database).filter(
                    Database.data_source_id == data_source_id,
                    Table.is_active == True
                )
                
                if business_domain:
                    query = query.filter(Database.business_domain == business_domain)
                
                tables = query.all()
                
                table_list = []
                for table in tables:
                    table_info = {
                        'id': str(table.id),
                        'name': table.name,
                        'display_name': table.display_name,
                        'database': table.database.name,
                        'database_display_name': table.database.display_name,
                        'table_type': table.table_type.value if table.table_type else 'table',
                        'row_count': table.row_count,
                        'size_mb': table.size_mb,
                        'business_tags': table.business_tags,
                        'data_sensitivity': table.data_sensitivity,
                        'last_analyzed': table.last_analyzed.isoformat() if table.last_analyzed else None
                    }
                    table_list.append(table_info)
                
                return table_list
                
        except Exception as e:
            self.logger.error(f"Error getting available tables: {e}")
            raise
    
    async def get_table_schema(self, table_id: str) -> Dict[str, Any]:
        """
        获取表的详细结构信息
        
        Args:
            table_id: 表ID
            
        Returns:
            表结构信息
        """
        try:
            from app.db.session import get_db_session
            from app.models.table_schema import Table, TableColumn
            
            with get_db_session() as db:
                table = db.query(Table).filter(Table.id == table_id).first()
                if not table:
                    raise ValueError(f"Table {table_id} not found")
                
                columns = db.query(TableColumn).filter(
                    TableColumn.table_id == table_id
                ).order_by(TableColumn.ordinal_position).all()
                
                column_list = []
                for column in columns:
                    column_info = {
                        'name': column.name,
                        'display_name': column.display_name,
                        'data_type': column.data_type.value if column.data_type else 'unknown',
                        'raw_type': column.raw_type,
                        'is_nullable': column.is_nullable,
                        'is_primary_key': column.is_primary_key,
                        'is_foreign_key': column.is_foreign_key,
                        'default_value': column.default_value,
                        'comment': column.column_comment,
                        'business_meaning': column.business_meaning,
                        'ordinal_position': column.ordinal_position
                    }
                    column_list.append(column_info)
                
                schema_info = {
                    'table_id': str(table.id),
                    'name': table.name,
                    'display_name': table.display_name,
                    'database': table.database.name,
                    'table_type': table.table_type.value if table.table_type else 'table',
                    'columns': column_list,
                    'row_count': table.row_count,
                    'size_mb': table.size_mb,
                    'business_tags': table.business_tags,
                    'data_sensitivity': table.data_sensitivity
                }
                
                return schema_info
                
        except Exception as e:
            self.logger.error(f"Error getting table schema: {e}")
            raise
    
    async def suggest_queries(self, data_source_id: str, business_context: Optional[str] = None) -> List[str]:
        """
        基于数据结构建议可能的查询
        
        Args:
            data_source_id: 数据源ID
            business_context: 业务上下文（可选）
            
        Returns:
            建议的查询列表
        """
        try:
            tables = await self.get_available_tables(data_source_id)
            
            suggestions = []
            
            # 基于表名和业务标签生成建议
            for table in tables:
                table_name = table['display_name'] or table['name']
                
                # 基础查询建议
                suggestions.append(f"查询{table_name}的所有数据")
                suggestions.append(f"统计{table_name}的数量")
                
                # 基于业务标签的建议
                if table.get('business_tags'):
                    for tag in table['business_tags']:
                        suggestions.append(f"分析{tag}相关的{table_name}数据")
                
                # 时间相关建议
                suggestions.append(f"查询{table_name}最近30天的数据")
                suggestions.append(f"按月统计{table_name}的趋势")
            
            # 跨表查询建议
            if len(tables) > 1:
                suggestions.append("查询不同表之间的关联关系")
                suggestions.append("生成跨表的综合报告")
            
            return suggestions[:10]  # 返回前10个建议
            
        except Exception as e:
            self.logger.error(f"Error generating query suggestions: {e}")
            return []
    
    async def explain_query(self, query: str, data_source_id: str) -> Dict[str, Any]:
        """
        解释查询的执行计划和涉及的表
        
        Args:
            query: 自然语言查询
            data_source_id: 数据源ID
            
        Returns:
            查询解释信息
        """
        try:
            # 生成查询计划
            query_plan = await self.query_router.route_query(query, data_source_id)
            
            explanation = {
                'original_query': query,
                'parsed_intent': query_plan.estimated_complexity,  # 简化处理
                'involved_tables': [],
                'join_conditions': query_plan.join_conditions,
                'filters': query_plan.where_conditions,
                'aggregations': query_plan.group_by_columns,
                'complexity': query_plan.estimated_complexity,
                'cross_database': query_plan.cross_database,
                'execution_strategy': '跨数据库查询' if query_plan.cross_database else '单数据库查询'
            }
            
            # 添加涉及的表信息
            for table_candidate in query_plan.primary_tables + query_plan.join_tables:
                table_info = {
                    'name': table_candidate.table.name,
                    'display_name': table_candidate.table.display_name,
                    'database': table_candidate.table.database.name,
                    'relevance_score': table_candidate.relevance_score,
                    'role': '主表' if table_candidate in query_plan.primary_tables else '关联表'
                }
                explanation['involved_tables'].append(table_info)
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Error explaining query: {e}")
            raise
    
    # 私有方法
    async def _ensure_metadata_discovered(self, data_source_id: str):
        """确保元数据已发现"""
        cache_key = f"metadata_discovered_{data_source_id}"
        
        if cache_key not in self._metadata_cache:
            self.logger.info(f"Discovering metadata for data source: {data_source_id}")
            await self.metadata_service.discover_data_source_metadata(data_source_id)
            self._metadata_cache[cache_key] = (True, datetime.now())
    
    async def _build_response(
        self,
        request: AgentQueryRequest,
        query_plan: QueryPlan,
        execution_result: ExecutionResult,
        start_time: datetime
    ) -> AgentQueryResponse:
        """构建查询响应"""
        
        # 生成查询解释
        explanation_parts = []
        explanation_parts.append(f"查询意图: {query_plan.estimated_complexity}")
        explanation_parts.append(f"涉及表数: {len(query_plan.primary_tables + query_plan.join_tables)}")
        
        if query_plan.cross_database:
            explanation_parts.append("执行了跨数据库查询")
        
        if execution_result.success:
            explanation_parts.append(f"成功返回 {execution_result.row_count} 行数据")
        
        explanation = "; ".join(explanation_parts)
        
        # 提取SQL查询
        sql_queries = [execution_result.query_sql] if execution_result.query_sql else []
        
        # 构建元数据信息
        metadata = {
            'query_complexity': query_plan.estimated_complexity,
            'cross_database': query_plan.cross_database,
            'tables_involved': len(query_plan.primary_tables + query_plan.join_tables),
            'joins_count': len(query_plan.join_conditions)
        }
        
        # 性能统计
        total_time = (datetime.now() - start_time).total_seconds()
        performance_stats = {
            'total_time': total_time,
            'execution_time': execution_result.execution_time,
            'routing_time': total_time - execution_result.execution_time
        }
        
        if execution_result.performance_stats:
            performance_stats.update(execution_result.performance_stats)
        
        return AgentQueryResponse(
            success=execution_result.success,
            data=execution_result.data.to_dict('records') if execution_result.data is not None else None,
            explanation=explanation,
            sql_queries=sql_queries,
            metadata=metadata,
            performance_stats=performance_stats,
            errors=execution_result.errors
        )