"""
多库多表智能Agent - 为Agent提供统一的多库多表访问能力
"""
import asyncio
import logging
import re
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
    
    def __init__(self, db_session=None, user_id=None):
        self.logger = logging.getLogger(__name__)
        self.metadata_service = MetadataDiscoveryService()
        self.query_router = IntelligentQueryRouter()
        self.executor = CrossDatabaseExecutor()
        self.user_id = user_id
        
        # 初始化AI服务
        try:
            from app.services.agents.core.ai_service import UnifiedAIService
            # 如果提供了用户ID，使用用户特定的AI服务
            if user_id and db_session:
                from app.core.ai_service_factory import UserAIServiceFactory
                factory = UserAIServiceFactory()
                self.ai_service = factory.get_user_ai_service(user_id)
                self.logger.info(f"使用用户特定AI服务: {user_id}")
            else:
                # 使用系统默认AI服务
                self.ai_service = UnifiedAIService(db_session=db_session)
                self.logger.info("使用系统默认AI服务")
        except Exception as e:
            self.logger.warning(f"AI服务初始化失败: {e}")
            # 尝试回退到系统默认服务
            try:
                self.ai_service = UnifiedAIService(db_session=db_session)
                self.logger.info("回退到系统默认AI服务")
            except Exception as e2:
                self.logger.error(f"系统默认AI服务也失败: {e2}")
                self.ai_service = None
        
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
    
    async def analyze_placeholder_requirements(self, agent_input: Dict[str, Any], execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析占位符需求并生成对应的SQL查询 - 智能分析架构
        使用AI驱动的分析和智能表选择机制
        
        Args:
            agent_input: 占位符分析输入
            execution_context: 执行时间上下文
        
        Returns:
            分析结果，包含高质量的SQL和相关信息
        """
        analysis_start_time = datetime.now()
        placeholder_name = agent_input.get('placeholder_name', '')
        placeholder_type = agent_input.get('placeholder_type', '')
        
        try:
            self.logger.info(f"🚀 开始Agent分析占位符: {placeholder_name}")
            
            # 提取占位符信息
            data_source = agent_input.get('data_source', {})
            data_source_id = data_source.get('id', '')
            schema_info = agent_input.get('schema_info', {})
            
            # 参数验证
            if not data_source_id:
                raise ValueError("数据源ID不能为空")
            if not placeholder_name:
                raise ValueError("占位符名称不能为空")
            
            self.logger.info(f"📊 占位符类型: {placeholder_type}, 数据源: {data_source_id}")
            
            # 1. 获取实时数据源结构信息 - 基于AI语义筛选
            self.logger.info("🔍 获取数据源结构信息...")
            enhanced_schema = await self._get_enhanced_schema_info(data_source_id, placeholder_name)
            
            if not enhanced_schema.get('table_schemas'):
                self.logger.warning("⚠️ 未获取到表结构信息，使用回退方案")
                return await self._create_fallback_solution(placeholder_name, data_source_id)
            
            relevant_tables = list(enhanced_schema.get('table_schemas', {}).keys())
            self.logger.info(f"✅ 获取到 {len(relevant_tables)} 个相关表: {relevant_tables}")
            
            # 2. 根据占位符类型选择分析方法
            analysis_mode = "ai_agent" if placeholder_type in ["statistic", "statistical", "analysis", "chart", "table"] else "semantic"
            self.logger.info(f"🧠 使用 {analysis_mode} 分析模式")
            
            if analysis_mode == "ai_agent":
                # 使用AI Agent进行深度分析
                semantic_analysis = await self._perform_ai_agent_analysis(
                    placeholder_name, placeholder_type, enhanced_schema, data_source
                )
                self.logger.info(f"🎯 AI分析完成: {semantic_analysis.get('intent', 'unknown')}")
            else:
                # 使用语义分析作为后备
                semantic_analysis = await self._analyze_placeholder_semantics(
                    placeholder_name, placeholder_type, enhanced_schema
                )
                self.logger.info(f"📋 语义分析完成: {semantic_analysis.get('intent', 'unknown')}")
            
            # 3. 智能字段选择和表选择
            self.logger.info("🎯 执行智能目标选择...")
            target_selection = await self._intelligent_target_selection(
                semantic_analysis, enhanced_schema
            )
            self.logger.info(f"✅ 智能目标选择完成: 表={target_selection.get('table', 'unknown')}, 字段数={len(target_selection.get('fields', []))}")
            
            # 4. 生成初始SQL（基于真实表结构）
            self.logger.info("⚙️ 生成智能SQL...")
            initial_sql = await self._generate_intelligent_sql(
                semantic_analysis, target_selection, enhanced_schema
            )
            self.logger.info(f"✅ 生成智能SQL: {initial_sql}")
            
            # 5. SQL质量验证和自我修正
            self.logger.info("🔧 执行SQL质量验证和改进...")
            validated_sql = await self._self_validate_and_improve_sql(
                initial_sql, data_source_id, target_selection
            )
            
            # 6. 应用执行时间参数替换
            if execution_context and execution_context.get("sql_parameters"):
                validated_sql = self._apply_sql_parameter_substitution(validated_sql, execution_context["sql_parameters"])
                self.logger.info(f"Applied SQL parameter substitution with {len(execution_context['sql_parameters'])} parameters")
            
            # 7. 计算增强置信度
            confidence_score = self._calculate_enhanced_confidence_score(
                semantic_analysis, target_selection, validated_sql
            )
            
            # 8. 计算分析耗时
            analysis_duration = (datetime.now() - analysis_start_time).total_seconds()
            
            # 9. 构建增强的返回结果
            result = {
                "success": True,
                "target_database": target_selection.get('database', 'default'),
                "target_table": target_selection.get('table', 'default_table'),
                "required_fields": target_selection.get('fields', ['*']),
                "generated_sql": validated_sql,
                "confidence_score": confidence_score,
                "analysis_metadata": {
                    "placeholder_name": placeholder_name,
                    "placeholder_type": placeholder_type,
                    "analysis_mode": analysis_mode,
                    "intent": semantic_analysis.get('intent', ''),
                    "data_operation": semantic_analysis.get('data_operation', ''),
                    "business_domain": semantic_analysis.get('business_domain', ''),
                    "relevant_tables_count": len(relevant_tables),
                    "analysis_duration_seconds": round(analysis_duration, 3),
                    "ai_service_available": self.ai_service is not None
                },
                "reasoning": semantic_analysis.get('reasoning', ''),
                "suggested_optimizations": semantic_analysis.get('optimizations', []),
                "estimated_execution_time": target_selection.get('estimated_time', 1000),
                "schema_quality": enhanced_schema.get('quality_metrics', {}),
                "field_mapping": target_selection.get('field_mapping', {}),
                "quality_metrics": {
                    "table_relevance": len(relevant_tables),
                    "field_coverage": len(target_selection.get('fields', [])),
                    "sql_complexity": len(validated_sql.split()) if validated_sql else 0
                }
            }
            
            self.logger.info(f"✅ Agent分析完成: {placeholder_name}")
            self.logger.info(f"📊 分析结果: 表={result['target_table']}, 置信度={confidence_score:.2f}, 耗时={analysis_duration:.3f}s")
            return result
            
        except Exception as e:
            analysis_duration = (datetime.now() - analysis_start_time).total_seconds()
            self.logger.error(f"❌ Agent分析失败: {placeholder_name}, 错误: {e}, 耗时: {analysis_duration:.3f}s")
            
            # 创建回退解决方案
            try:
                fallback_result = await self._create_fallback_solution(placeholder_name, data_source_id)
                fallback_result.update({
                    "analysis_metadata": {
                        "placeholder_name": placeholder_name,
                        "placeholder_type": placeholder_type,
                        "analysis_mode": "fallback",
                        "analysis_duration_seconds": round(analysis_duration, 3),
                        "error": str(e),
                        "ai_service_available": self.ai_service is not None
                    }
                })
                return fallback_result
            except Exception as fallback_error:
                self.logger.error(f"❌ 回退方案也失败: {fallback_error}")
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_error": str(fallback_error),
                    "generated_sql": "SELECT 1 as placeholder_value",
                    "target_table": "unknown",
                    "confidence_score": 0.0,
                    "analysis_metadata": {
                        "placeholder_name": placeholder_name,
                        "placeholder_type": placeholder_type,
                        "analysis_mode": "emergency_fallback",
                        "analysis_duration_seconds": round(analysis_duration, 3),
                        "error": str(e)
                    }
                }
    
    def _build_natural_query_from_placeholder(self, placeholder_name: str, placeholder_type: str, schema_info: Dict) -> str:
        """从占位符信息构建自然语言查询"""
        # 解析占位符名称中的语义信息
        name_parts = placeholder_name.lower().split(':')
        if len(name_parts) >= 2:
            category = name_parts[0]  # 如："统计", "区域", "周期"
            metric = name_parts[1]    # 如："总数", "地区名称", "开始日期"
            
            # 构建更智能的查询
            if '统计' in category or 'count' in metric or '数量' in metric or '件数' in metric:
                return f"统计 {metric} 的总数"
            elif '区域' in category or '地区' in metric:
                return f"获取 {metric} 信息"
            elif '周期' in category or '日期' in metric or '时间' in metric:
                return f"获取 {metric} 的时间信息"
            elif '占比' in metric or '百分比' in metric:
                return f"计算 {metric} 的比例"
        
        # 回退到简单的查询
        return f"查询与 {placeholder_name} 相关的数据"
    
    def _generate_sql_from_query_plan(self, query_plan, schema_info: Dict) -> str:
        """基于查询计划和增强的schema信息生成更精确的SQL"""
        if not query_plan.primary_tables:
            # 使用schema_info中的表信息
            tables = schema_info.get('tables', [])
            if tables:
                best_table = self._select_best_table_from_schema(schema_info)
                return f"SELECT COUNT(*) as count FROM {best_table}"
            return "SELECT COUNT(*) as count FROM default_table"
        
        primary_table = query_plan.primary_tables[0].table
        table_name = primary_table.name
        
        # 从增强的schema信息中获取表的详细结构
        table_schemas = schema_info.get('table_schemas', {})
        table_schema = table_schemas.get(table_name, {})
        
        # 基于查询计划和表结构生成更智能的SQL
        if query_plan.aggregate_functions:
            # 包含聚合函数
            agg_func = query_plan.aggregate_functions[0]
            if 'count' in agg_func.lower():
                sql = f"SELECT COUNT(*) as total_count FROM {table_name}"
            elif 'sum' in agg_func.lower():
                # 尝试找到数值字段进行求和
                numeric_field = self._find_numeric_field(table_schema)
                if numeric_field:
                    sql = f"SELECT SUM({numeric_field}) as total_sum FROM {table_name}"
                else:
                    sql = f"SELECT COUNT(*) as total_count FROM {table_name}"
            elif 'avg' in agg_func.lower():
                # 尝试找到数值字段进行平均值计算
                numeric_field = self._find_numeric_field(table_schema)
                if numeric_field:
                    sql = f"SELECT AVG({numeric_field}) as avg_value FROM {table_name}"
                else:
                    sql = f"SELECT COUNT(*) as total_count FROM {table_name}"
            else:
                sql = f"SELECT {agg_func} FROM {table_name}"
        else:
            # 基于表结构生成合适的字段列表
            important_fields = self._select_important_fields(table_schema)
            if important_fields:
                fields_str = ', '.join(important_fields[:5])  # 限制字段数量
                sql = f"SELECT {fields_str} FROM {table_name}"
            else:
                sql = f"SELECT * FROM {table_name}"
        
        # 添加WHERE条件
        if query_plan.where_conditions:
            sql += f" WHERE {' AND '.join(query_plan.where_conditions)}"
        
        # 添加智能LIMIT（基于表大小）
        table_metadata = table_schema.get('metadata', {})
        estimated_rows = table_metadata.get('estimated_rows', 0)
        if estimated_rows > 10000:
            sql += " LIMIT 50"  # 大表限制更少行数
        else:
            sql += " LIMIT 100"
        
        self.logger.info(f"Generated enhanced SQL: {sql}")
        return sql
    
    def _calculate_confidence_score(self, query_plan, placeholder_name: str, schema_info: Dict) -> float:
        """计算分析的置信度分数"""
        base_score = 0.5
        
        # 如果找到了相关表，提高置信度
        if query_plan.primary_tables:
            base_score += 0.3
        
        # 如果占位符名称与表字段匹配，提高置信度
        if self._has_matching_fields(placeholder_name, schema_info):
            base_score += 0.2
        
        # 限制在0-1范围内
        return min(1.0, base_score)
    
    def _extract_required_fields(self, query_plan) -> List[str]:
        """从查询计划中提取需要的字段"""
        if query_plan.select_columns:
            return query_plan.select_columns
        return ["*"]
    
    def _suggest_optimizations(self, query_plan) -> List[str]:
        """建议查询优化"""
        optimizations = []
        
        if query_plan.estimated_complexity > 5:
            optimizations.append("考虑添加索引以提高查询性能")
        
        if query_plan.cross_database:
            optimizations.append("跨数据库查询，考虑数据缓存策略")
        
        if len(query_plan.join_tables) > 3:
            optimizations.append("多表JOIN，建议检查查询计划")
        
        return optimizations
    
    def _apply_sql_parameter_substitution(self, sql: str, sql_parameters: Dict[str, str]) -> str:
        """应用SQL参数替换，支持时间相关的动态参数"""
        try:
            substituted_sql = sql
            
            # 按参数长度排序，确保较长的参数先被替换（避免部分匹配问题）
            sorted_parameters = sorted(sql_parameters.items(), key=lambda x: len(x[0]), reverse=True)
            
            for parameter, value in sorted_parameters:
                if parameter in substituted_sql:
                    substituted_sql = substituted_sql.replace(parameter, value)
                    self.logger.debug(f"Replaced {parameter} with {value}")
            
            # 记录替换后的SQL用于调试
            if substituted_sql != sql:
                self.logger.info(f"Original SQL: {sql}")
                self.logger.info(f"Substituted SQL: {substituted_sql}")
            
            return substituted_sql
            
        except Exception as e:
            self.logger.error(f"Error applying SQL parameter substitution: {e}")
            # 出错时返回原SQL
            return sql
    
    def _has_matching_fields(self, placeholder_name: str, schema_info: Dict) -> bool:
        """检查占位符名称是否与数据库字段匹配"""
        placeholder_lower = placeholder_name.lower()
        
        # 检查schema_info中的实际字段
        table_schemas = schema_info.get('table_schemas', {})
        for table_name, table_schema in table_schemas.items():
            columns = table_schema.get('columns', [])
            for column in columns:
                column_name = column.get('name', '').lower()
                if any(keyword in placeholder_lower for keyword in [column_name]):
                    return True
        
        # 回退到关键词匹配
        common_keywords = ['count', 'sum', 'total', 'date', 'time', 'name', 'id']
        return any(keyword in placeholder_lower for keyword in common_keywords)
    
    def _select_best_table_from_schema(self, schema_info: Dict) -> str:
        """从schema信息中选择最佳表"""
        tables = schema_info.get('tables', [])
        table_schemas = schema_info.get('table_schemas', {})
        
        if not tables:
            return "default_table"
        
        # 基于表的业务相关性选择
        best_table = tables[0]
        best_score = 0.0
        
        for table_name in tables:
            table_schema = table_schemas.get(table_name, {})
            metadata = table_schema.get('metadata', {})
            relevance = metadata.get('business_relevance', 0.0)
            
            if relevance > best_score:
                best_score = relevance
                best_table = table_name
        
        return best_table
    
    def _find_numeric_field(self, table_schema: Dict) -> str:
        """在表结构中查找数值字段"""
        columns = table_schema.get('columns', [])
        
        # 优先查找明显的数值字段
        for column in columns:
            column_name = column.get('name', '').lower()
            column_type = column.get('type', '').lower()
            
            # 基于字段名判断
            if any(keyword in column_name for keyword in ['amount', 'price', 'cost', 'value', 'count', 'num']):
                return column.get('name', '')
            
            # 基于字段类型判断
            if any(type_keyword in column_type for type_keyword in ['int', 'float', 'decimal', 'number', 'bigint']):
                return column.get('name', '')
        
        return None
    
    def _select_important_fields(self, table_schema: Dict) -> List[str]:
        """选择表中重要的字段"""
        columns = table_schema.get('columns', [])
        important_fields = []
        
        # 优先级字段关键词
        priority_keywords = ['id', 'name', 'title', 'status', 'date', 'time', 'created', 'updated']
        
        # 先添加优先级字段
        for column in columns:
            column_name = column.get('name', '')
            if any(keyword in column_name.lower() for keyword in priority_keywords):
                important_fields.append(column_name)
        
        # 如果重要字段不够，添加其他字段
        if len(important_fields) < 3:
            for column in columns:
                column_name = column.get('name', '')
                if column_name not in important_fields:
                    important_fields.append(column_name)
                    if len(important_fields) >= 5:
                        break
        
        return important_fields
    
    async def _get_enhanced_schema_info(self, data_source_id: str, placeholder_name: str = "") -> Dict[str, Any]:
        """获取增强的数据源结构信息 - 完全使用新API"""
        try:
            from app.models.data_source import DataSource
            from app.services.connectors.connector_factory import create_connector
            from app.db.session import get_db_session
            
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"数据源 {data_source_id} 不存在")
                
                connector = create_connector(data_source)
                await connector.connect()
                
                try:
                    # 使用新API获取完整信息
                    databases = await connector.get_databases()
                    tables = await connector.get_tables()
                    
                    # 基于LLM进行智能表选择
                    relevant_tables = await self._ai_select_relevant_tables(tables, placeholder_name)
                    self.logger.info(f"基于AI语义分析筛选到 {len(relevant_tables)} 个相关表: {relevant_tables}")
                    
                    # 获取相关表的详细结构
                    table_schemas = {}
                    for table_name in relevant_tables:
                        try:
                            schema_info = await connector.get_table_schema(table_name)
                            table_schemas[table_name] = schema_info
                            
                            # 增强字段分析
                            columns = schema_info.get('columns', [])
                            schema_info['enhanced_metadata'] = {
                                'business_fields': self._identify_business_fields(columns),
                                'key_fields': self._identify_key_fields(columns),
                                'numeric_fields': self._identify_numeric_fields(columns),
                                'date_fields': self._identify_date_fields(columns),
                                'text_fields': self._identify_text_fields(columns)
                            }
                            
                        except Exception as e:
                            self.logger.warning(f"获取表 {table_name} 结构失败: {e}")
                    
                    enhanced_schema = {
                        'data_source_id': data_source_id,
                        'data_source_name': data_source.name,
                        'databases': databases,
                        'tables': tables,
                        'table_schemas': table_schemas,
                        'quality_metrics': {
                            'total_tables': len(tables),
                            'analyzed_tables': len(table_schemas),
                            'coverage_rate': (len(table_schemas) / len(tables)) * 100 if tables else 0,
                            'total_fields': sum(len(schema.get('columns', [])) for schema in table_schemas.values())
                        },
                        'retrieved_at': datetime.now().isoformat(),
                        'source': 'enhanced_connector_api'
                    }
                    
                    self.logger.info(f"获取增强schema完成: {len(tables)}个表, {enhanced_schema['quality_metrics']['total_fields']}个字段")
                    return enhanced_schema
                    
                finally:
                    await connector.disconnect()
                    
        except Exception as e:
            self.logger.error(f"获取增强schema信息失败: {e}")
            return {
                'data_source_id': data_source_id,
                'error': str(e),
                'databases': [],
                'tables': [],
                'table_schemas': {},
                'quality_metrics': {'total_tables': 0, 'analyzed_tables': 0, 'coverage_rate': 0}
            }
    
    async def _analyze_placeholder_semantics(self, placeholder_name: str, placeholder_type: str, enhanced_schema: Dict) -> Dict[str, Any]:
        """智能分析占位符语义"""
        try:
            analysis = {
                'placeholder_name': placeholder_name,
                'placeholder_type': placeholder_type,
                'intent': None,
                'business_domain': None,
                'data_operation': None,
                'temporal_scope': None,
                'aggregation_type': None,
                'reasoning': []
            }
            
            name_lower = placeholder_name.lower()
            
            # 意图分析
            if any(kw in name_lower for kw in ['统计', 'count', '数量', '件数', '总计']):
                analysis['intent'] = 'statistical'
                analysis['data_operation'] = 'count'
                analysis['aggregation_type'] = 'COUNT'
                analysis['reasoning'].append('识别为统计类占位符')
            elif any(kw in name_lower for kw in ['区域', '地区', '地点', 'region', 'area']):
                analysis['intent'] = 'dimensional'
                analysis['data_operation'] = 'group_by'
                analysis['business_domain'] = 'geographic'
                analysis['reasoning'].append('识别为地理维度占位符')
            elif any(kw in name_lower for kw in ['周期', '时间', '日期', 'date', 'time', 'period']):
                analysis['intent'] = 'temporal'
                analysis['data_operation'] = 'filter'
                analysis['temporal_scope'] = 'date_range'
                analysis['reasoning'].append('识别为时间周期占位符')
            elif any(kw in name_lower for kw in ['金额', '费用', '价格', 'amount', 'price', 'cost']):
                analysis['intent'] = 'financial'
                analysis['data_operation'] = 'sum'
                analysis['aggregation_type'] = 'SUM'
                analysis['reasoning'].append('识别为金额类占位符')
            else:
                analysis['intent'] = 'general'
                analysis['data_operation'] = 'select'
                analysis['reasoning'].append('识别为一般查询占位符')
            
            # 业务领域分析
            if any(kw in name_lower for kw in ['投诉', 'complaint', '举报', '反馈']):
                analysis['business_domain'] = 'complaint_management'
                analysis['reasoning'].append('识别为投诉管理业务域')
            elif any(kw in name_lower for kw in ['旅行', '旅游', 'travel', 'tour']):
                analysis['business_domain'] = 'travel_business'
                analysis['reasoning'].append('识别为旅游业务域')
            elif any(kw in name_lower for kw in ['用户', '客户', 'user', 'customer']):
                analysis['business_domain'] = 'customer_management'
                analysis['reasoning'].append('识别为客户管理业务域')
            
            # 优化建议
            analysis['optimizations'] = self._generate_semantic_optimizations(analysis)
            
            self.logger.info(f"占位符语义分析完成: {placeholder_name} -> {analysis['intent']}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"占位符语义分析失败: {e}")
            return {
                'placeholder_name': placeholder_name,
                'intent': 'general',
                'data_operation': 'select',
                'reasoning': [f'分析失败，使用默认配置: {str(e)}']
            }
    
    async def _intelligent_target_selection(self, semantic_analysis: Dict, enhanced_schema: Dict) -> Dict[str, Any]:
        """智能目标表和字段选择"""
        try:
            table_schemas = enhanced_schema.get('table_schemas', {})
            
            # 表选择评分
            table_scores = {}
            for table_name, schema in table_schemas.items():
                score = 0.0
                
                # 基于业务域匹配
                business_domain = semantic_analysis.get('business_domain', '')
                if business_domain == 'complaint_management':
                    if any(kw in table_name.lower() for kw in ['complaint', 'report', 'feedback']):
                        score += 3.0
                elif business_domain == 'travel_business':
                    if any(kw in table_name.lower() for kw in ['travel', 'tour', 'booking']):
                        score += 3.0
                elif business_domain == 'customer_management':
                    if any(kw in table_name.lower() for kw in ['user', 'customer', 'member']):
                        score += 3.0
                
                # 基于字段丰富度
                columns = schema.get('columns', [])
                enhanced_metadata = schema.get('enhanced_metadata', {})
                
                score += len(columns) * 0.1  # 字段数量加分
                score += len(enhanced_metadata.get('business_fields', [])) * 0.5  # 业务字段加分
                score += len(enhanced_metadata.get('key_fields', [])) * 0.3  # 关键字段加分
                
                table_scores[table_name] = score
            
            # 选择最佳表
            if table_scores:
                best_table = max(table_scores, key=table_scores.get)
                best_schema = table_schemas[best_table]
            else:
                # 回退到第一个可用表
                tables = enhanced_schema.get('tables', [])
                best_table = tables[0] if tables else 'default_table'
                best_schema = table_schemas.get(best_table, {})
            
            # 智能字段选择
            selected_fields = self._select_optimal_fields(semantic_analysis, best_schema)
            
            # 构建字段映射
            field_mapping = self._create_field_mapping(semantic_analysis, best_schema)
            
            result = {
                'database': enhanced_schema.get('databases', ['default'])[0] if enhanced_schema.get('databases') else 'default',
                'table': best_table,
                'fields': selected_fields,
                'field_mapping': field_mapping,
                'table_score': table_scores.get(best_table, 0.0),
                'estimated_time': self._estimate_query_time(best_schema, selected_fields),
                'selection_reasoning': f'选择表 {best_table}，评分: {table_scores.get(best_table, 0.0):.2f}'
            }
            
            self.logger.info(f"智能目标选择完成: 表={best_table}, 字段数={len(selected_fields)}")
            return result
            
        except Exception as e:
            self.logger.error(f"智能目标选择失败: {e}")
            return {
                'database': 'default',
                'table': 'default_table',
                'fields': ['*'],
                'field_mapping': {},
                'selection_reasoning': f'选择失败，使用默认值: {str(e)}'
            }
    
    async def _generate_intelligent_sql(self, semantic_analysis: Dict, target_selection: Dict, enhanced_schema: Dict) -> str:
        """基于语义分析和目标选择生成智能SQL - 优化版本"""
        try:
            table_name = target_selection.get('table', 'default_table')
            fields = target_selection.get('fields', [])
            field_mapping = target_selection.get('field_mapping', {})
            
            # 验证表名
            if not table_name or not isinstance(table_name, str):
                self.logger.warning(f"无效的表名: {table_name}")
                return self._generate_fallback_sql()
            
            # 清理表名，确保安全
            table_name = self._sanitize_identifier(table_name)
            
            # 尝试使用AI生成SQL
            ai_generated_sql = await self._generate_sql_with_ai(semantic_analysis, target_selection, enhanced_schema)
            
            if ai_generated_sql and self._validate_sql_syntax(ai_generated_sql):
                self.logger.info(f"AI生成SQL成功: {ai_generated_sql}")
                return ai_generated_sql
            
            # 如果AI生成失败，使用模板化SQL生成
            self.logger.info("AI生成SQL失败，使用模板化SQL生成")
            sql = self._generate_sql_by_template(semantic_analysis.get('intent', 'general'), 
                                               semantic_analysis.get('data_operation', 'select'), 
                                               table_name, fields, field_mapping)
            
            # 验证生成的SQL
            if not self._validate_sql_syntax(sql):
                self.logger.warning(f"生成的SQL语法无效，使用备用方案: {sql}")
                sql = self._generate_fallback_sql(table_name)
            
            self.logger.info(f"生成智能SQL: {sql}")
            return sql
            
        except Exception as e:
            self.logger.error(f"生成智能SQL失败: {e}")
            return self._generate_fallback_sql()
    
    async def _generate_sql_with_ai(self, semantic_analysis: Dict, target_selection: Dict, enhanced_schema: Dict) -> str:
        """使用AI生成SQL"""
        try:
            if not self.ai_service:
                self.logger.warning("AI服务不可用，跳过AI SQL生成")
                return None
            
            # 构建SQL生成提示
            sql_prompt = self._build_sql_generation_prompt(semantic_analysis, target_selection, enhanced_schema)
            
            # 构建上下文
            context = {
                "semantic_analysis": semantic_analysis,
                "target_selection": target_selection,
                "table_schema": enhanced_schema.get('table_schemas', {}).get(target_selection.get('table', ''), {})
            }
            
            # 调用AI服务生成SQL
            response = await self.ai_service.analyze_with_context(
                context=str(context),
                prompt=sql_prompt,
                task_type="sql_generation",
                use_cache=True,
                use_rate_limiter=True
            )
            
            if response:
                # 清理响应，提取SQL语句
                sql = self._extract_sql_from_response(response)
                if sql and self._validate_sql_syntax(sql):
                    return sql
            
            return None
            
        except Exception as e:
            self.logger.error(f"AI SQL生成失败: {e}")
            return None
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从AI响应中提取SQL语句"""
        if not response or not isinstance(response, str):
            return None
        
        # 清理响应文本
        response = response.strip()
        
        # 查找SQL语句的开始和结束
        sql_keywords = ['SELECT', 'select']
        for keyword in sql_keywords:
            if keyword in response:
                start_idx = response.find(keyword)
                # 找到SQL语句的结束（通常是分号或换行）
                end_idx = response.find(';', start_idx)
                if end_idx == -1:
                    # 如果没有分号，找到第一个换行符
                    end_idx = response.find('\n', start_idx)
                    if end_idx == -1:
                        end_idx = len(response)
                
                sql = response[start_idx:end_idx].strip()
                
                # 验证SQL语法
                if self._validate_sql_syntax(sql):
                    return sql
        
        return None
    
    def _generate_sql_by_template(self, intent: str, data_operation: str, table_name: str, fields: List[str], field_mapping: Dict) -> str:
        """使用模板生成SQL，避免字符串拼接错误"""
        
        # SQL模板定义
        sql_templates = {
            'statistical_count': "SELECT COUNT(*) as total_count FROM {table}",
            'statistical_sum': "SELECT SUM({field}) as total_sum FROM {table}",
            'statistical_avg': "SELECT AVG({field}) as average_value FROM {table}",
            'dimensional_group': "SELECT {group_field}, COUNT(*) as count FROM {table} GROUP BY {group_field}",
            'temporal_date': "SELECT DATE({date_field}) as date, COUNT(*) as count FROM {table} GROUP BY DATE({date_field})",
            'general_select': "SELECT {fields} FROM {table} LIMIT 100",
            'fallback_count': "SELECT COUNT(*) as total_count FROM {table}"
        }
        
        try:
            if intent == 'statistical':
                if data_operation == 'count':
                    return sql_templates['statistical_count'].format(table=table_name)
                elif data_operation == 'sum':
                    amount_field = field_mapping.get('amount_field')
                    if amount_field and self._is_valid_field_name(amount_field):
                        return sql_templates['statistical_sum'].format(field=amount_field, table=table_name)
                    else:
                        return sql_templates['statistical_count'].format(table=table_name)
                elif data_operation == 'avg':
                    numeric_field = field_mapping.get('numeric_field')
                    if numeric_field and self._is_valid_field_name(numeric_field):
                        return sql_templates['statistical_avg'].format(field=numeric_field, table=table_name)
                    else:
                        return sql_templates['statistical_count'].format(table=table_name)
                else:
                    return sql_templates['statistical_count'].format(table=table_name)
                    
            elif intent == 'dimensional':
                group_field = field_mapping.get('group_field')
                if group_field and self._is_valid_field_name(group_field):
                    return sql_templates['dimensional_group'].format(group_field=group_field, table=table_name)
                else:
                    return sql_templates['general_select'].format(fields='*', table=table_name)
                    
            elif intent == 'temporal':
                date_field = field_mapping.get('date_field')
                if date_field and self._is_valid_field_name(date_field):
                    return sql_templates['temporal_date'].format(date_field=date_field, table=table_name)
                else:
                    return sql_templates['general_select'].format(fields='*', table=table_name)
                    
            else:
                # 一般查询
                if fields and len(fields) > 0:
                    cleaned_fields = self._clean_field_names(fields[:5])
                    if cleaned_fields:
                        fields_str = ', '.join(cleaned_fields)
                        return sql_templates['general_select'].format(fields=fields_str, table=table_name)
                    else:
                        return sql_templates['fallback_count'].format(table=table_name)
                else:
                    return sql_templates['fallback_count'].format(table=table_name)
                    
        except Exception as e:
            self.logger.error(f"SQL模板生成失败: {e}")
            return sql_templates['fallback_count'].format(table=table_name)
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """清理和验证SQL标识符"""
        if not identifier or not isinstance(identifier, str):
            return 'default_table'
        
        # 移除危险字符，只保留字母、数字、下划线
        cleaned = ''.join(c for c in identifier if c.isalnum() or c == '_')
        
        # 确保不以数字开头
        if cleaned and cleaned[0].isdigit():
            cleaned = 't_' + cleaned
            
        # 确保不为空
        if not cleaned:
            cleaned = 'default_table'
            
        return cleaned
    
    def _is_valid_field_name(self, field_name: str) -> bool:
        """验证字段名是否有效"""
        if not field_name or not isinstance(field_name, str):
            return False
        
        # 检查是否只包含有效字符
        if not all(c.isalnum() or c in ['_', '.'] for c in field_name):
            return False
        
        # 检查是否为SQL关键字
        sql_keywords = {'select', 'from', 'where', 'group', 'by', 'order', 'limit', 'count', 'sum', 'avg', 'max', 'min'}
        if field_name.lower() in sql_keywords:
            return False
            
        return True
    
    def _clean_field_names(self, fields: List[str]) -> List[str]:
        """清理字段名列表"""
        cleaned_fields = []
        for field in fields:
            if field and isinstance(field, str):
                cleaned_field = self._sanitize_identifier(field)
                if cleaned_field and self._is_valid_field_name(cleaned_field):
                    cleaned_fields.append(cleaned_field)
        return cleaned_fields
    
    def _validate_sql_syntax(self, sql: str) -> bool:
        """基本的SQL语法验证"""
        if not sql or not isinstance(sql, str):
            return False
        
        sql_upper = sql.upper()
        
        # 检查基本结构
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 检查是否包含FROM
        if 'FROM' not in sql_upper:
            return False
        
        # 检查是否有明显的语法错误
        error_patterns = [
            'SELECTSELECT', 'FROMFROM', 'WHEREWHERE', 'GROUPGROUP', 'ORDERORDER',
            'SELECT*FROM', 'SELECTFROM', 'SELECT,FROM'
        ]
        
        for pattern in error_patterns:
            if pattern in sql_upper:
                return False
        
        return True
    
    def _generate_fallback_sql(self, table_name: str = 'default_table') -> str:
        """生成备用SQL"""
        safe_table = self._sanitize_identifier(table_name)
        return f"SELECT COUNT(*) as total_count FROM {safe_table}"
    
    async def _self_validate_and_improve_sql(self, sql: str, data_source_id: str, target_selection: Dict) -> str:
        """SQL质量验证和自我改进 - 增强版本"""
        try:
            # 第0轮：基本语法检查
            if not self._validate_sql_syntax(sql):
                self.logger.warning(f"SQL语法验证失败，尝试修复: {sql}")
                sql = self._fix_sql_syntax_errors(sql)
                if not self._validate_sql_syntax(sql):
                    self.logger.error(f"SQL语法修复失败，使用备用SQL")
                    return self._generate_fallback_sql(target_selection.get('table', 'default_table'))
            
            from app.models.data_source import DataSource
            from app.services.connectors.connector_factory import create_connector
            from app.db.session import get_db_session
            
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    return sql
                
                connector = create_connector(data_source)
                await connector.connect()
                
                try:
                    # 第1轮：表存在性验证
                    tables = await connector.get_tables()
                    sql = self._validate_and_fix_table_names(sql, tables)
                    
                    # 第2轮：字段存在性验证
                    table_name = target_selection.get('table')
                    if table_name and table_name in tables:
                        schema_info = await connector.get_table_schema(table_name)
                        sql = self._validate_and_fix_field_names(sql, schema_info, target_selection)
                    
                    # 第3轮：性能优化
                    sql = self._optimize_sql_performance(sql, target_selection)
                    
                    # 第4轮：最终语法验证
                    if not self._validate_sql_syntax(sql):
                        self.logger.warning(f"最终SQL语法验证失败，使用备用SQL: {sql}")
                        return self._generate_fallback_sql(table_name)
                    
                    self.logger.info(f"SQL验证和改进完成: {sql}")
                    return sql
                    
                finally:
                    await connector.disconnect()
                    
        except Exception as e:
            self.logger.error(f"SQL验证和改进失败: {e}")
            return self._generate_fallback_sql(target_selection.get('table', 'default_table'))
    
    def _fix_sql_syntax_errors(self, sql: str) -> str:
        """修复常见的SQL语法错误"""
        if not sql or not isinstance(sql, str):
            return self._generate_fallback_sql()
        
        # 修复常见的语法错误模式
        fixes = [
            # 修复重复的SELECT
            (r'SELECT\s+SELECT', 'SELECT'),
            (r'SELECT\s+FROM', 'SELECT * FROM'),
            (r'SELECT\s*,', 'SELECT *,'),
            (r'SELECT\s*FROM', 'SELECT * FROM'),
            
            # 修复字段名错误
            (r'SELEid', 'SELECT id'),
            (r's_idT', 'SELECT'),
            (r's_idOUNT', 'COUNT'),
            
            # 修复表名错误
            (r'FROM\s+FROM', 'FROM'),
            (r'FROM\s*,', 'FROM'),
            
            # 修复WHERE子句错误
            (r'WHERE\s+WHERE', 'WHERE'),
            (r'WHERE\s*,', 'WHERE'),
            
            # 修复GROUP BY错误
            (r'GROUP\s+GROUP', 'GROUP'),
            (r'GROUP\s*,', 'GROUP'),
            
            # 修复ORDER BY错误
            (r'ORDER\s+ORDER', 'ORDER'),
            (r'ORDER\s*,', 'ORDER'),
        ]
        
        fixed_sql = sql
        for pattern, replacement in fixes:
            fixed_sql = re.sub(pattern, replacement, fixed_sql, flags=re.IGNORECASE)
        
        # 如果修复后仍然有问题，使用备用SQL
        if not self._validate_sql_syntax(fixed_sql):
            self.logger.warning(f"SQL语法修复后仍无效，使用备用SQL: {fixed_sql}")
            return self._generate_fallback_sql()
        
        return fixed_sql
    
    # 新增的辅助方法
    def _identify_business_fields(self, columns: List[Dict]) -> List[str]:
        """识别业务相关字段"""
        business_fields = []
        for col in columns:
            name = col.get('name', '').lower()
            if any(kw in name for kw in ['name', 'title', 'desc', 'type', 'status', 'category', 'region', 'area']):
                business_fields.append(col.get('name', ''))
        return business_fields
    
    def _identify_key_fields(self, columns: List[Dict]) -> List[str]:
        """识别关键字段（主键、外键等）"""
        key_fields = []
        for col in columns:
            name = col.get('name', '').lower()
            if col.get('key') == 'PRI' or 'id' in name or col.get('key') == 'UNI':
                key_fields.append(col.get('name', ''))
        return key_fields
    
    def _identify_numeric_fields(self, columns: List[Dict]) -> List[str]:
        """识别数值字段"""
        numeric_fields = []
        for col in columns:
            col_type = col.get('type', '').lower()
            name = col.get('name', '').lower()
            if any(t in col_type for t in ['int', 'float', 'decimal', 'double', 'numeric']) or \
               any(kw in name for kw in ['amount', 'price', 'cost', 'value', 'count', 'num']):
                numeric_fields.append(col.get('name', ''))
        return numeric_fields
    
    def _identify_date_fields(self, columns: List[Dict]) -> List[str]:
        """识别日期字段"""
        date_fields = []
        for col in columns:
            col_type = col.get('type', '').lower()
            name = col.get('name', '').lower()
            if any(t in col_type for t in ['date', 'time', 'timestamp']) or \
               any(kw in name for kw in ['date', 'time', 'created', 'updated', 'modified']):
                date_fields.append(col.get('name', ''))
        return date_fields
    
    async def _ai_select_relevant_tables(self, all_tables: List[str], placeholder_name: str) -> List[str]:
        """基于AI语义分析智能选择相关表"""
        if not placeholder_name or not self.ai_service:
            # 回退到规则匹配
            return self._select_relevant_tables(all_tables, placeholder_name)
        
        try:
            # 构建分析上下文
            context = f"""
数据库中有以下表：
{chr(10).join([f"- {table}" for table in all_tables])}

用户需求占位符: {placeholder_name}
"""
            
            # 构建分析提示
            prompt = """
作为数据分析专家，请分析用户需求占位符与数据表的相关性。

分析要求：
1. 理解占位符的业务含义和数据需求
2. 分析每个表名可能对应的业务功能
3. 选择最相关的1-3个表来满足该需求
4. 优先选择核心业务表，避免辅助表

请返回JSON格式的分析结果：
{
    "selected_tables": ["表名1", "表名2", "表名3"],
    "reasoning": {
        "表名1": "选择理由",
        "表名2": "选择理由"
    },
    "confidence": 0.9
}
"""
            
            # 调用AI服务
            response = await self.ai_service.analyze_with_context(
                context=context,
                prompt=prompt,
                task_type="intelligent_table_selection",
                use_cache=True,
                use_rate_limiter=True
            )
            
            # 解析AI响应
            if response:
                import json
                try:
                    result = json.loads(response)
                    selected_tables = result.get("selected_tables", [])
                    reasoning = result.get("reasoning", {})
                    confidence = result.get("confidence", 0.0)
                    
                    # 验证选择的表是否存在
                    valid_tables = [table for table in selected_tables if table in all_tables]
                    
                    self.logger.info(f"AI表选择结果: {valid_tables}, 置信度: {confidence}")
                    for table, reason in reasoning.items():
                        if table in valid_tables:
                            self.logger.info(f"  {table}: {reason}")
                    
                    return valid_tables[:3] if valid_tables else all_tables[:3]
                    
                except json.JSONDecodeError as e:
                    self.logger.warning(f"AI响应JSON解析失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"AI表选择失败: {e}")
            
        # 回退到规则匹配
        return self._select_relevant_tables(all_tables, placeholder_name)
    
    def _select_relevant_tables(self, all_tables: List[str], placeholder_name: str) -> List[str]:
        """基于占位符名称智能选择相关表"""
        if not placeholder_name:
            # 如果没有占位符名称，返回前5个表作为默认
            return all_tables[:5]
        
        # 提取占位符中的关键词
        keywords = self._extract_business_keywords(placeholder_name)
        relevant_tables = []
        scores = {}
        
        # 为每个表计算相关性分数
        for table in all_tables:
            score = 0
            table_lower = table.lower()
            
            # 基于关键词匹配计算分数
            for keyword in keywords:
                if keyword in table_lower:
                    score += 10  # 精确匹配得高分
                elif any(keyword in part for part in table_lower.split('_')):
                    score += 5   # 部分匹配得中等分
            
            # 基于表名常见模式的分数调整
            if any(pattern in table_lower for pattern in ['complain', 'complaint', 'feedback']):
                if any(kw in ['投诉', '反馈', '意见'] for kw in keywords):
                    score += 8
            
            if any(pattern in table_lower for pattern in ['user', 'customer', 'tourist', 'client']):
                if any(kw in ['用户', '客户', '游客', '身份证'] for kw in keywords):
                    score += 6
            
            if any(pattern in table_lower for pattern in ['order', 'travel', 'itinerary']):
                if any(kw in ['订单', '行程', '旅游'] for kw in keywords):
                    score += 6
            
            scores[table] = score
        
        # 选择得分最高的表，最多选择3个
        sorted_tables = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        relevant_tables = [table for table, score in sorted_tables if score > 0][:3]
        
        # 如果没有相关表，返回前3个表
        if not relevant_tables:
            relevant_tables = all_tables[:3]
        
        return relevant_tables
    
    def _extract_business_keywords(self, placeholder_name: str) -> List[str]:
        """从占位符名称中提取业务关键词"""
        # 移除常见的统计词汇，保留业务关键词
        business_terms = []
        name_lower = placeholder_name.lower()
        
        # 业务关键词映射
        keyword_mapping = {
            '投诉': ['complaint', 'complain'],
            '反馈': ['feedback'],
            '用户': ['user', 'customer'],
            '客户': ['customer', 'client'], 
            '游客': ['tourist', 'visitor'],
            '身份证': ['id_card', 'identity'],
            '微信': ['wechat', 'weixin'],
            '小程序': ['miniprogram', 'applet'],
            '订单': ['order'],
            '行程': ['itinerary', 'travel'],
            '住宿': ['accommodation', 'hotel'],
            '景区': ['scenic', 'attraction'],
            '导游': ['guide'],
            '退费': ['refund']
        }
        
        # 提取中文关键词
        for chinese, english_variants in keyword_mapping.items():
            if chinese in placeholder_name:
                business_terms.append(chinese)
                business_terms.extend(english_variants)
        
        return business_terms
    
    def _identify_text_fields(self, columns: List[Dict]) -> List[str]:
        """识别文本字段"""
        text_fields = []
        for col in columns:
            col_type = col.get('type', '').lower()
            if any(t in col_type for t in ['varchar', 'text', 'char', 'string']):
                text_fields.append(col.get('name', ''))
        return text_fields
    
    async def _perform_ai_agent_analysis(
        self, 
        placeholder_name: str, 
        placeholder_type: str, 
        enhanced_schema: Dict, 
        data_source: Dict
    ) -> Dict[str, Any]:
        """
        使用AI Agent进行深度占位符分析
        
        Args:
            placeholder_name: 占位符名称
            placeholder_type: 占位符类型
            enhanced_schema: 增强的数据库结构信息
            data_source: 数据源信息
            
        Returns:
            AI分析结果
        """
        try:
            # 构建上下文信息
            context = {
                "placeholder_name": placeholder_name,
                "placeholder_type": placeholder_type,
                "available_tables": enhanced_schema.get('tables', []),  # 修复：tables是列表，不是字典
                "table_relationships": enhanced_schema.get('relationships', []),
                "business_domain": enhanced_schema.get('business_domain', ''),
                "data_source_type": data_source.get('source_type', '')
            }
            
            # 构建AI分析提示
            analysis_prompt = self._build_ai_analysis_prompt(context, enhanced_schema)
            
            # 使用AI服务进行分析
            if not self.ai_service:
                raise Exception("AI服务未初始化")
            
            # 如果AI服务支持用户特定配置，记录用户信息
            if hasattr(self.ai_service, 'user_id') and self.ai_service.user_id:
                self.logger.info(f"使用用户特定AI服务进行分析: {self.ai_service.user_id}")
            else:
                self.logger.info("使用系统默认AI服务进行分析")
            
            response = await self.ai_service.analyze_with_context(
                context=str(context),
                prompt=analysis_prompt,
                task_type=f"placeholder_agent_analysis_{placeholder_type}",
                use_cache=True,
                use_rate_limiter=True
            )
            
            # 调试：查看AI响应内容
            self.logger.info(f"AI响应内容: {response[:200]}...")  # 只显示前200个字符
            
            # 解析AI响应
            ai_result = None
            if response:
                try:
                    import json
                    # 尝试直接解析JSON
                    ai_result = {
                        "success": True,
                        "data": json.loads(response)
                    }
                    self.logger.info("AI响应JSON解析成功")
                except json.JSONDecodeError as e:
                    self.logger.warning(f"AI响应JSON解析失败: {e}")
                    self.logger.warning(f"AI响应原始内容: {response}")
                    
                    # 尝试提取JSON部分
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        try:
                            json_str = response[json_start:json_end]
                            ai_result = {
                                "success": True,
                                "data": json.loads(json_str)
                            }
                            self.logger.info("从响应中提取JSON成功")
                        except json.JSONDecodeError:
                            self.logger.error("提取的JSON仍然无效")
                            # 如果不是JSON，尝试解析为文本
                            ai_result = {
                                "success": True,
                                "data": {
                                    "intent": "statistical",
                                    "data_operation": "count",
                                    "reasoning": [response]
                                }
                            }
                    else:
                        # 如果没有找到JSON，返回文本响应
                        ai_result = {
                            "success": True,
                            "data": {
                                "intent": "statistical",
                                "data_operation": "count",
                                "reasoning": [response]
                            }
                        }
            
            if ai_result and ai_result.get("success"):
                analysis_data = ai_result.get("data", {})
                
                return {
                    "intent": analysis_data.get("intent", "statistical"),
                    "data_operation": analysis_data.get("data_operation", "count"),
                    "business_domain": analysis_data.get("business_domain", ""),
                    "target_metrics": analysis_data.get("target_metrics", []),
                    "time_dimension": analysis_data.get("time_dimension"),
                    "grouping_dimensions": analysis_data.get("grouping_dimensions", []),
                    "filters": analysis_data.get("filters", []),
                    "aggregations": analysis_data.get("aggregations", ["count"]),
                    "reasoning": analysis_data.get("reasoning", []),
                    "confidence": analysis_data.get("confidence", 0.8),
                    "optimizations": analysis_data.get("optimizations", [])
                }
            else:
                # AI分析失败时回退到语义分析
                self.logger.warning(f"AI分析失败，回退到语义分析: {ai_result.get('error', 'Unknown error')}")
                return await self._analyze_placeholder_semantics(placeholder_name, placeholder_type, enhanced_schema)
                
        except Exception as e:
            self.logger.error(f"AI Agent分析失败: {e}")
            # 回退到语义分析
            return await self._analyze_placeholder_semantics(placeholder_name, placeholder_type, enhanced_schema)
    
    def _build_ai_analysis_prompt(self, context: Dict, enhanced_schema: Dict) -> str:
        """构建AI分析提示 - 优化版本"""
        
        placeholder_name = context["placeholder_name"]
        placeholder_type = context["placeholder_type"]
        available_tables = context["available_tables"]
        
        # 获取表结构详情
        table_details = []
        for table_name, table_info in enhanced_schema.get('table_schemas', {}).items():
            columns = table_info.get('columns', [])
            column_names = [col.get('name', col.get('Field', '')) for col in columns]
            table_details.append(f"- {table_name}: {', '.join(column_names[:10])}")  # 限制显示的字段数量
        
        prompt = f"""
你是一个专业的数据分析师。请分析以下占位符的业务需求，并返回JSON格式的分析结果。

占位符信息：
- 名称: {placeholder_name}
- 类型: {placeholder_type}
- 业务领域: {context.get('business_domain', '未知')}

可用数据表结构：
{chr(10).join(table_details[:5])}  # 限制显示的表数量

请严格按照以下JSON格式返回分析结果，不要包含任何其他文本：

{{
    "intent": "statistical",
    "data_operation": "count",
    "business_domain": "travel_service",
    "target_metrics": ["导游数量"],
    "time_dimension": null,
    "grouping_dimensions": [],
    "filters": ["city_id = '昆明'"],
    "aggregations": ["count"],
    "reasoning": ["根据占位符名称，目标是统计昆明注册的导游数量"],
    "confidence": 0.9,
    "optimizations": ["考虑建立索引在city_id字段上"]
}}

重要要求：
1. 只返回JSON对象，不要包含任何解释、注释或其他文本
2. 确保JSON语法完全正确
3. 字段名必须是数据库中实际存在的字段名
4. 聚合函数必须是标准的SQL聚合函数

请直接返回JSON对象，不要有任何前缀或后缀。
"""
        
        return prompt
    
    def _build_sql_generation_prompt(self, semantic_analysis: Dict, target_selection: Dict, enhanced_schema: Dict) -> str:
        """构建专门的SQL生成提示"""
        
        table_name = target_selection.get('table', '')
        fields = target_selection.get('fields', [])
        intent = semantic_analysis.get('intent', '')
        data_operation = semantic_analysis.get('data_operation', '')
        
        # 获取表结构信息
        table_schema = enhanced_schema.get('table_schemas', {}).get(table_name, {})
        columns = table_schema.get('columns', [])
        column_names = [col.get('name', '') for col in columns if col.get('name')]
        
        prompt = f"""
你是一个专业的SQL专家。请根据以下信息生成准确、有效的SQL查询语句。

分析信息：
- 业务意图: {intent}
- 数据操作: {data_operation}
- 目标表: {table_name}
- 可用字段: {', '.join(column_names[:20])}  # 限制显示字段数量

SQL生成要求：
1. 生成标准的SQL SELECT语句
2. 使用正确的表名和字段名
3. 根据业务意图选择合适的聚合函数
4. 添加适当的WHERE条件（如果需要）
5. 使用LIMIT限制结果数量（建议100行以内）

SQL模板示例：
- 统计查询: SELECT COUNT(*) as total_count FROM {table_name}
- 求和查询: SELECT SUM(amount_field) as total_amount FROM {table_name}
- 分组查询: SELECT group_field, COUNT(*) as count FROM {table_name} GROUP BY group_field
- 时间查询: SELECT DATE(date_field) as date, COUNT(*) as count FROM {table_name} GROUP BY DATE(date_field)

请只返回SQL语句，不要包含任何解释、注释或其他内容。确保SQL语法完全正确。
"""
        
        return prompt
    
    def _generate_semantic_optimizations(self, analysis: Dict) -> List[str]:
        """生成语义优化建议"""
        optimizations = []
        intent = analysis.get('intent', '')
        
        if intent == 'statistical':
            optimizations.append('考虑添加适当的WHERE条件过滤无效数据')
            optimizations.append('对于大表建议使用索引优化COUNT查询')
        elif intent == 'dimensional':
            optimizations.append('考虑为分组字段添加索引')
            optimizations.append('限制分组结果数量避免过多维度')
        elif intent == 'temporal':
            optimizations.append('为日期字段添加索引以优化时间范围查询')
            optimizations.append('考虑使用日期分区提升查询性能')
        
        return optimizations
    
    def _select_optimal_fields(self, semantic_analysis: Dict, schema: Dict) -> List[str]:
        """选择最优字段组合"""
        enhanced_metadata = schema.get('enhanced_metadata', {})
        all_columns = [col.get('name') for col in schema.get('columns', []) if col.get('name')]
        
        intent = semantic_analysis.get('intent', 'general')
        
        # 清理字段名称的辅助函数
        def clean_field_names(fields):
            cleaned = []
            for field in fields:
                if field and isinstance(field, str):
                    # 确保字段名称只包含有效字符
                    clean_field = ''.join(c for c in field if c.isalnum() or c in ['_'])
                    if clean_field and not clean_field.isdigit():  # 避免纯数字字段名
                        cleaned.append(clean_field)
            return cleaned
        
        if intent == 'statistical':
            # 统计查询使用计数，但在SQL生成阶段处理
            return []  # 返回空，让SQL生成阶段决定使用COUNT(*)
        elif intent == 'dimensional':
            # 维度查询需要分组字段
            business_fields = enhanced_metadata.get('business_fields', [])
            fields = business_fields[:3] if business_fields else all_columns[:3]
            return clean_field_names(fields)
        elif intent == 'temporal':
            # 时间查询需要日期字段
            date_fields = enhanced_metadata.get('date_fields', [])
            fields = date_fields[:2] if date_fields else all_columns[:2]
            return clean_field_names(fields)
        else:
            # 一般查询选择关键字段
            key_fields = enhanced_metadata.get('key_fields', [])
            business_fields = enhanced_metadata.get('business_fields', [])
            selected = list(set(key_fields[:2] + business_fields[:3]))
            fields = selected if selected else all_columns[:5]
            return clean_field_names(fields)
    
    def _create_field_mapping(self, semantic_analysis: Dict, schema: Dict) -> Dict[str, str]:
        """创建字段映射"""
        enhanced_metadata = schema.get('enhanced_metadata', {})
        mapping = {}
        
        intent = semantic_analysis.get('intent', '')
        
        if intent == 'financial':
            numeric_fields = enhanced_metadata.get('numeric_fields', [])
            if numeric_fields:
                mapping['amount_field'] = numeric_fields[0]
        elif intent == 'dimensional':
            business_fields = enhanced_metadata.get('business_fields', [])
            if business_fields:
                mapping['group_field'] = business_fields[0]
        elif intent == 'temporal':
            date_fields = enhanced_metadata.get('date_fields', [])
            if date_fields:
                mapping['date_field'] = date_fields[0]
        
        return mapping
    
    def _estimate_query_time(self, schema: Dict, fields: List[str]) -> int:
        """估算查询时间（毫秒）"""
        base_time = 100
        
        # 基于字段数量
        field_count = len(fields)
        if field_count > 10:
            base_time += field_count * 10
        
        # 基于表大小（如果有的话）
        estimated_rows = schema.get('estimated_rows', 1000)
        if estimated_rows > 100000:
            base_time += 500
        elif estimated_rows > 10000:
            base_time += 200
        
        return base_time
    
    def _calculate_enhanced_confidence_score(self, semantic_analysis: Dict, target_selection: Dict, sql: str) -> float:
        """计算增强的置信度分数"""
        base_score = 0.3
        
        # 语义分析质量
        if semantic_analysis.get('intent') != 'general':
            base_score += 0.2
        
        if semantic_analysis.get('business_domain'):
            base_score += 0.2
        
        # 目标选择质量
        table_score = target_selection.get('table_score', 0.0)
        if table_score > 2.0:
            base_score += 0.2
        elif table_score > 1.0:
            base_score += 0.1
        
        # SQL复杂度
        if 'COUNT' in sql.upper() or 'SUM' in sql.upper():
            base_score += 0.1
        
        return min(1.0, base_score)
    
    async def _create_fallback_solution(self, placeholder_name: str, data_source_id: str) -> Dict[str, Any]:
        """创建降级解决方案"""
        try:
            # 简单的降级SQL
            if '统计' in placeholder_name or 'count' in placeholder_name.lower():
                sql = "SELECT COUNT(*) as count FROM information_schema.tables"
                reasoning = "使用系统表进行计数查询"
            elif '时间' in placeholder_name or 'date' in placeholder_name.lower():
                sql = "SELECT NOW() as current_time"
                reasoning = "返回当前时间作为时间占位符"
            else:
                sql = "SELECT 'placeholder_value' as value"
                reasoning = "返回静态占位符值"
            
            return {
                'sql': sql,
                'reasoning': reasoning
            }
        except Exception:
            return {
                'sql': "SELECT 1 as placeholder_value",
                'reasoning': "最基础的降级方案"
            }
    
    def _basic_sql_validation(self, sql: str) -> bool:
        """基础SQL语法验证"""
        sql_upper = sql.upper().strip()
        
        # 必须以SELECT开始
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 必须包含FROM（除非是简单的常量查询）
        if 'FROM' not in sql_upper and 'NOW()' not in sql_upper and not any(op in sql_upper for op in ['1', '2', '3', '4', '5', '6', '7', '8', '9']):
            return False
        
        # 不能包含危险关键词
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE']
        if any(keyword in sql_upper for keyword in dangerous):
            return False
        
        return True
    
    def _fix_basic_syntax(self, sql: str) -> str:
        """修复基础语法错误"""
        # 修复常见拼写错误
        corrections = {
            'SELET': 'SELECT',
            'SELCT': 'SELECT',
            'FORM': 'FROM',
            'WHRE': 'WHERE',
            'GRUP': 'GROUP',
            'OEDER': 'ORDER'
        }
        
        for wrong, correct in corrections.items():
            sql = sql.replace(wrong, correct)
        
        # 确保以SELECT开始
        if not sql.upper().strip().startswith('SELECT'):
            sql = f"SELECT COUNT(*) FROM ({sql}) as subquery"
        
        return sql
    
    def _validate_and_fix_table_names(self, sql: str, available_tables: List[str]) -> str:
        """验证和修复表名"""
        import re
        
        # 提取表名
        table_pattern = r'FROM\s+([`"]?)(\w+)\1'
        matches = re.findall(table_pattern, sql, re.IGNORECASE)
        
        for quote, table_name in matches:
            if table_name not in available_tables:
                # 查找最相似的表
                best_match = self._find_similar_table(table_name, available_tables)
                if best_match:
                    sql = sql.replace(f'FROM {quote}{table_name}{quote}', f'FROM {quote}{best_match}{quote}')
                    self.logger.info(f"表名修复: {table_name} -> {best_match}")
        
        return sql
    
    def _validate_and_fix_field_names(self, sql: str, schema_info: Dict, target_selection: Dict) -> str:
        """验证和修复字段名"""
        available_fields = [col.get('name') for col in schema_info.get('columns', [])]
        
        # 如果查询字段不存在，替换为安全的字段
        if not available_fields:
            return sql
        
        # 简单的字段替换策略
        if 'SELECT *' not in sql.upper():
            # 如果不是SELECT *，确保使用存在的字段
            safe_fields = available_fields[:3]  # 使用前3个字段
            field_pattern = r'SELECT\s+([^FROM]+)'
            match = re.search(field_pattern, sql, re.IGNORECASE)
            if match:
                sql = sql.replace(match.group(1), ', '.join(safe_fields))
        
        return sql
    
    def _optimize_sql_performance(self, sql: str, target_selection: Dict) -> str:
        """SQL性能优化"""
        # 添加LIMIT以防止大结果集
        if 'LIMIT' not in sql.upper():
            if 'COUNT(' in sql.upper() or 'SUM(' in sql.upper() or 'AVG(' in sql.upper():
                # 聚合查询不需要LIMIT
                pass
            else:
                sql += ' LIMIT 100'
        
        return sql
    
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