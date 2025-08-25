"""
占位符SQL构建Agent

独立的Agent，专门负责基于占位符和数据库表结构构建SQL查询能力
基于上下文工程设计，支持任务板块和模版占位符分析板块调用
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from ..core import (
    ContextAwareAgent, AgentContext, ContextScope,
    get_context_manager, get_agent_registry
)
from ...domain.placeholder.semantic_analyzer import (
    PlaceholderSemanticAnalyzer, create_semantic_analyzer, SemanticAnalysisResult
)
from ...domain.placeholder.intelligent_sql_generator import (
    IntelligentSQLGenerator, create_intelligent_sql_generator, 
    TableContext, SQLGenerationResult
)
from ..enhanced_placeholder_analyzer import (
    EnhancedPlaceholderAnalyzer, create_enhanced_placeholder_analyzer,
    EnhancedSemanticAnalysisResult, DataSourceContext
)

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderAnalysisRequest:
    """占位符分析请求"""
    placeholder_id: str
    placeholder_text: str
    placeholder_type: str
    data_source_id: str
    template_id: Optional[str] = None
    template_context: Optional[Dict[str, Any]] = None
    force_reanalyze: bool = False
    store_result: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlaceholderAnalysisResult:
    """占位符分析结果"""
    success: bool
    placeholder_id: str
    generated_sql: Optional[str] = None
    confidence: float = 0.0
    semantic_type: Optional[str] = None
    semantic_subtype: Optional[str] = None
    data_intent: Optional[str] = None
    target_table: Optional[str] = None
    explanation: Optional[str] = None
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
    analysis_timestamp: datetime = None
    
    def __post_init__(self):
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()
        if self.suggestions is None:
            self.suggestions = []
        if self.metadata is None:
            self.metadata = {}
        if self.error_context is None:
            self.error_context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['analysis_timestamp'] = self.analysis_timestamp.isoformat()
        return result


class PlaceholderSQLAgent(ContextAwareAgent):
    """占位符SQL构建Agent - 独立的、基于上下文工程的Agent"""
    
    def __init__(self, db_session: Session = None, user_id: str = None):
        # 初始化上下文管理器
        context_manager = get_context_manager()
        
        super().__init__("placeholder_sql_agent", context_manager)
        
        self.db_session = db_session
        self.user_id = user_id
        
        # 初始化核心组件
        self.semantic_analyzer = create_semantic_analyzer()
        self.sql_generator = create_intelligent_sql_generator()
        
        # 初始化LLM增强分析器
        try:
            self.enhanced_analyzer = create_enhanced_placeholder_analyzer(
                db_session=db_session, user_id=user_id
            )
            logger.info("LLM增强分析器初始化成功")
        except Exception as e:
            logger.warning(f"LLM增强分析器初始化失败: {e}，将回退到规则分析器")
            self.enhanced_analyzer = None
        
        # 注册Agent能力
        self._register_capabilities()
        
        # 声明所需的上下文（但是这些在实际使用中是可选的）
        # 注释掉必需上下文的声明，因为我们会在获取schema时动态获取
        # self.require_context(
        #     'data_source_schemas',
        #     'table_structures', 
        #     'placeholder_history',
        #     'analysis_patterns'
        # )
        
        logger.info(f"PlaceholderSQLAgent initialized for user: {user_id}")
    
    def _register_capabilities(self):
        """注册Agent能力"""
        
        # 主要能力：占位符分析与SQL生成
        self.register_capability(
            "analyze_placeholder_sql",
            "分析占位符并生成SQL查询",
            metadata={
                "input_schema": {
                    "request": {
                        "type": "object",
                        "properties": {
                            "placeholder_id": {"type": "string", "required": True},
                            "placeholder_text": {"type": "string", "required": True},
                            "data_source_id": {"type": "string", "required": True},
                            "force_reanalyze": {"type": "boolean", "default": False},
                            "store_result": {"type": "boolean", "default": True}
                        }
                    }
                },
                "output_schema": {
                    "result": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "generated_sql": {"type": "string"},
                            "confidence": {"type": "number"},
                            "semantic_type": {"type": "string"},
                            "target_table": {"type": "string"}
                        }
                    }
                },
                "tags": ["sql", "placeholder", "analysis"],
                "requirements": ["database_access", "schema_access"]
            }
        )
        
        # 批量分析能力
        self.register_capability(
            "batch_analyze_placeholders",
            "批量分析多个占位符",
            metadata={
                "input_schema": {
                    "requests": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "output_schema": {
                    "results": {
                        "type": "array", 
                        "items": {"type": "object"}
                    }
                },
                "tags": ["sql", "placeholder", "batch"],
                "requirements": ["database_access", "schema_access"]
            }
        )
        
        # 检查已存储SQL能力
        self.register_capability(
            "check_stored_sql",
            "检查占位符是否已有存储的SQL",
            metadata={
                "input_schema": {
                    "placeholder_id": {"type": "string", "required": True}
                },
                "output_schema": {
                    "has_sql": {"type": "boolean"},
                    "sql": {"type": "string"},
                    "last_analysis_at": {"type": "string"}
                },
                "tags": ["sql", "storage", "check"],
                "requirements": ["database_access"]
            }
        )
    
    async def _execute_action(self, context: AgentContext, action: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的Agent操作"""
        
        if action == "analyze_placeholder_sql":
            return await self._analyze_placeholder_sql(context, parameters)
        elif action == "batch_analyze_placeholders":
            return await self._batch_analyze_placeholders(context, parameters)
        elif action == "check_stored_sql":
            return await self._check_stored_sql(context, parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _analyze_placeholder_sql(self, context: AgentContext, 
                                     parameters: Dict[str, Any]) -> Dict[str, Any]:
        """分析占位符并生成SQL"""
        
        try:
            # 构建分析请求
            request = PlaceholderAnalysisRequest(
                placeholder_id=parameters.get('placeholder_id'),
                placeholder_text=parameters.get('placeholder_text'),
                placeholder_type=parameters.get('placeholder_type', 'unknown'),
                data_source_id=parameters.get('data_source_id'),
                template_id=parameters.get('template_id'),
                template_context=parameters.get('template_context'),
                force_reanalyze=parameters.get('force_reanalyze', False),
                store_result=parameters.get('store_result', True)
            )
            
            # 检查是否已有存储的SQL（如果不强制重新分析）
            if not request.force_reanalyze:
                stored_result = await self._get_stored_sql(request.placeholder_id)
                if stored_result:
                    self.update_context(
                        context, 'last_operation', 
                        'retrieved_stored_sql', 
                        ContextScope.REQUEST
                    )
                    return {"result": stored_result.to_dict()}
            
            # 更新上下文
            self.update_context(
                context, 'current_analysis_request', 
                request.to_dict(), 
                ContextScope.REQUEST
            )
            
            # 获取数据源Schema信息
            schema_info = await self._get_schema_info(context, request.data_source_id)
            if not schema_info:
                return {
                    "result": PlaceholderAnalysisResult(
                        success=False,
                        placeholder_id=request.placeholder_id,
                        error_message="无法获取数据源schema信息",
                        error_context={"data_source_id": request.data_source_id}
                    ).to_dict()
                }
            
            # 尝试使用LLM增强分析器
            if self.enhanced_analyzer:
                try:
                    enhanced_result = await self._analyze_with_llm(
                        request, schema_info, context
                    )
                    if enhanced_result.success:
                        logger.info(f"LLM分析成功: {request.placeholder_id}")
                        return {"result": enhanced_result.to_dict()}
                    else:
                        logger.warning(f"LLM分析失败，回退到规则分析器: {request.placeholder_id}")
                except Exception as e:
                    logger.error(f"LLM分析异常: {e}，回退到规则分析器")
            
            # 回退到规则分析器
            logger.info(f"使用规则分析器处理: {request.placeholder_id}")
            
            # 语义分析
            semantic_result = self.semantic_analyzer.analyze(
                request.placeholder_text,
                context={
                    'template_context': request.template_context or {},
                    'data_source_id': request.data_source_id
                }
            )
            
            # 构建表上下文
            table_context = await self._build_table_context(schema_info, semantic_result)
            if not table_context:
                return {
                    "result": PlaceholderAnalysisResult(
                        success=False,
                        placeholder_id=request.placeholder_id,
                        error_message="无法构建表上下文",
                        error_context={"schema_info": "no_suitable_table"}
                    ).to_dict()
                }
            
            # SQL生成
            sql_result = self.sql_generator.generate_sql(
                semantic_result=semantic_result,
                table_context=table_context,
                placeholder_name=request.placeholder_text,
                additional_context=request.template_context or {}
            )
            
            # 构建结果
            analysis_result = PlaceholderAnalysisResult(
                success=True,
                placeholder_id=request.placeholder_id,
                generated_sql=sql_result.sql,
                confidence=sql_result.confidence,
                semantic_type=semantic_result.primary_type.value,
                semantic_subtype=semantic_result.sub_type,
                data_intent=semantic_result.data_intent,
                target_table=table_context.table_name,
                explanation=sql_result.explanation,
                suggestions=sql_result.suggestions,
                metadata={
                    'semantic_analysis': {
                        'primary_type': semantic_result.primary_type.value,
                        'sub_type': semantic_result.sub_type,
                        'keywords': semantic_result.keywords,
                        'confidence': semantic_result.confidence
                    },
                    'sql_generation': {
                        'parameters': sql_result.parameters,
                        'metadata': sql_result.metadata
                    },
                    'table_context': {
                        'table_name': table_context.table_name,
                        'business_category': table_context.business_category,
                        'data_quality_score': table_context.data_quality_score
                    }
                }
            )
            
            # 存储结果到数据库（如果需要）
            if request.store_result:
                await self._store_analysis_result(analysis_result)
            
            # 更新上下文
            self.update_context(
                context, 'last_analysis_result', 
                analysis_result.to_dict(), 
                ContextScope.TASK
            )
            
            return {"result": analysis_result.to_dict()}
            
        except Exception as e:
            logger.error(f"占位符分析失败: {e}", exc_info=True)
            
            error_result = PlaceholderAnalysisResult(
                success=False,
                placeholder_id=parameters.get('placeholder_id', 'unknown'),
                error_message=str(e),
                error_context={'exception_type': type(e).__name__}
            )
            
            return {"result": error_result.to_dict()}
    
    async def _batch_analyze_placeholders(self, context: AgentContext, 
                                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """批量分析占位符"""
        
        requests = parameters.get('requests', [])
        results = []
        
        for request_data in requests:
            try:
                result = await self._analyze_placeholder_sql(context, request_data)
                results.append(result['result'])
            except Exception as e:
                error_result = PlaceholderAnalysisResult(
                    success=False,
                    placeholder_id=request_data.get('placeholder_id', 'unknown'),
                    error_message=str(e)
                )
                results.append(error_result.to_dict())
        
        return {
            "results": results,
            "total_count": len(requests),
            "success_count": len([r for r in results if r.get('success')])
        }
    
    async def _check_stored_sql(self, context: AgentContext, 
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """检查已存储的SQL"""
        
        placeholder_id = parameters.get('placeholder_id')
        stored_result = await self._get_stored_sql(placeholder_id)
        
        if stored_result and stored_result.success and stored_result.generated_sql:
            return {
                "has_sql": True,
                "sql": stored_result.generated_sql,
                "last_analysis_at": stored_result.analysis_timestamp.isoformat(),
                "confidence": stored_result.confidence,
                "target_table": stored_result.target_table
            }
        else:
            return {
                "has_sql": False,
                "sql": None,
                "last_analysis_at": None
            }
    
    async def _get_schema_info(self, context: AgentContext, 
                             data_source_id: str) -> Optional[Dict[str, Any]]:
        """获取数据源Schema信息"""
        
        try:
            from ...data.schemas.schema_query_service import SchemaQueryService
            from ...data.schemas.schema_discovery_service import SchemaDiscoveryService
            
            if not self.db_session:
                logger.error("数据库会话未初始化")
                return None
                
            schema_service = SchemaQueryService(self.db_session)
            table_schemas = schema_service.get_table_schemas(data_source_id)
            
            if not table_schemas:
                logger.warning(f"数据源 {data_source_id} 没有缓存的表结构信息，尝试自动获取")
                
                # 自动触发schema发现
                try:
                    discovery_service = SchemaDiscoveryService(self.db_session)
                    discovery_result = await discovery_service.discover_and_store_schemas(data_source_id)
                    
                    if discovery_result.get("success"):
                        logger.info(f"自动schema发现成功，发现 {discovery_result.get('tables_count', 0)} 个表")
                        # 重新获取表结构
                        table_schemas = schema_service.get_table_schemas(data_source_id)
                    else:
                        logger.error(f"自动schema发现失败: {discovery_result.get('error')}")
                        return None
                        
                except Exception as discovery_e:
                    logger.error(f"自动schema发现异常: {discovery_e}")
                    return None
                
            if not table_schemas:
                return None
            
            # 构建schema信息
            schema_info = {
                'data_source_id': data_source_id,
                'tables': [],
                'table_details': {}
            }
            
            for table_schema in table_schemas:
                table_name = table_schema.table_name
                schema_info['tables'].append(table_name)
                
                # 获取表的列信息
                columns = schema_service.get_table_columns(table_schema.id)
                column_details = []
                
                for column in columns:
                    column_info = {
                        "name": column.column_name,
                        "type": column.column_type,
                        "normalized_type": column.normalized_type or "unknown",
                        "nullable": column.is_nullable,
                        "primary_key": column.is_primary_key,
                        "business_name": column.business_name,
                        "business_description": column.business_description,
                        "semantic_category": column.semantic_category,
                        "sample_values": column.sample_values,
                        "data_patterns": column.data_patterns
                    }
                    column_details.append(column_info)
                
                schema_info['table_details'][table_name] = {
                    "columns": column_details,
                    "business_category": table_schema.business_category,
                    "data_freshness": table_schema.data_freshness,
                    "update_frequency": table_schema.update_frequency,
                    "estimated_row_count": table_schema.estimated_row_count,
                    "data_quality_score": table_schema.data_quality_score
                }
            
            # 更新上下文
            self.update_context(
                context, 'current_schema_info', 
                schema_info, 
                ContextScope.REQUEST
            )
            
            return schema_info
            
        except Exception as e:
            logger.error(f"获取Schema信息失败: {e}")
            return None
    
    async def _build_table_context(self, schema_info: Dict[str, Any], 
                                 semantic_result: SemanticAnalysisResult) -> Optional[TableContext]:
        """基于语义分析结果构建最佳表上下文"""
        
        try:
            if not schema_info.get('tables'):
                return None
            
            # 智能选择最佳表
            best_table = self._select_best_table(schema_info, semantic_result)
            if not best_table:
                return None
            
            table_info = schema_info['table_details'].get(best_table, {})
            columns = table_info.get("columns", [])
            
            # 提取主键与日期列
            primary_keys = []
            date_columns = []
            
            for col in columns:
                col_name = col.get("name", "")
                normalized_type = (col.get("normalized_type") or "").lower()
                raw_type = (col.get("type") or "").lower()
                
                if col.get("primary_key"):
                    primary_keys.append(col_name)
                
                # 识别日期列
                if (any(k in col_name.lower() for k in ["date", "dt", "time", "day", "month", "year"]) or
                    any(k in normalized_type for k in ["date", "time"]) or
                    any(k in raw_type for k in ["date", "time", "timestamp"])):
                    date_columns.append(col_name)
            
            # 构建TableContext - 安全处理 None 值
            def safe_float(value, default=0.0):
                """安全地将值转换为float，处理None情况"""
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                """安全地将值转换为int，处理None情况"""
                if value is None:
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            return TableContext(
                table_name=best_table,
                columns=columns,
                business_category=table_info.get("business_category"),
                estimated_rows=safe_int(table_info.get("estimated_row_count"), 0),
                primary_keys=primary_keys,
                date_columns=date_columns,
                data_freshness=table_info.get("data_freshness"),
                update_frequency=table_info.get("update_frequency"),
                data_quality_score=safe_float(table_info.get("data_quality_score"), 0.0),
                completeness_rate=safe_float(table_info.get("completeness_rate"), 0.0),
                accuracy_rate=safe_float(table_info.get("accuracy_rate"), 0.0)
            )
            
        except Exception as e:
            logger.error(f"构建表上下文失败: {e}")
            return None
    
    def _select_best_table(self, schema_info: Dict[str, Any], 
                          semantic_result: SemanticAnalysisResult) -> Optional[str]:
        """智能选择最佳目标表"""
        
        tables = schema_info.get('tables', [])
        if not tables:
            return None
        
        table_details = schema_info.get('table_details', {})
        
        # 根据语义类型进行表选择
        if semantic_result.primary_type.value == "temporal":
            # 时间相关查询，优先选择有时间字段的表
            for table_name in tables:
                table_info = table_details.get(table_name, {})
                columns = table_info.get("columns", [])
                for col in columns:
                    col_name = col.get("name", "").lower()
                    if any(k in col_name for k in ["date", "time", "year", "dt"]):
                        return table_name
        
        elif semantic_result.primary_type.value == "dimensional":
            # 维度查询，优先选择有地区、分类字段的表
            for table_name in tables:
                table_info = table_details.get(table_name, {})
                columns = table_info.get("columns", [])
                for col in columns:
                    col_name = col.get("name", "").lower()
                    if any(k in col_name for k in ["region", "area", "city", "category", "type"]):
                        return table_name
        
        # 优先选择数据质量高的表
        best_table = None
        best_score = -1
        
        for table_name in tables:
            table_info = table_details.get(table_name, {})
            # 安全地处理可能的 None 值
            quality_score_raw = table_info.get("data_quality_score", 0.0)
            if quality_score_raw is None:
                quality_score = 0.0
            else:
                try:
                    quality_score = float(quality_score_raw)
                except (ValueError, TypeError):
                    quality_score = 0.0
            
            if quality_score > best_score:
                best_score = quality_score
                best_table = table_name
        
        # 如果有数据质量评分，返回最佳表
        if best_table and best_score > 0:
            return best_table
        
        # 默认返回第一个表
        return tables[0]
    
    async def _get_stored_sql(self, placeholder_id: str) -> Optional[PlaceholderAnalysisResult]:
        """获取已存储的SQL分析结果"""
        
        try:
            from ....models.template_placeholder import TemplatePlaceholder
            
            if not self.db_session:
                return None
                
            placeholder = (
                self.db_session.query(TemplatePlaceholder)
                .filter(TemplatePlaceholder.id == placeholder_id)
                .first()
            )
            
            if placeholder and placeholder.generated_sql:
                # 从数据库记录构建结果
                metadata = placeholder.parsing_metadata or {}
                semantic_analysis = metadata.get('semantic_analysis', {})
                
                return PlaceholderAnalysisResult(
                    success=True,
                    placeholder_id=placeholder_id,
                    generated_sql=placeholder.generated_sql,
                    confidence=metadata.get('confidence', 0.8),
                    semantic_type=semantic_analysis.get('primary_type'),
                    semantic_subtype=semantic_analysis.get('sub_type'),
                    data_intent=semantic_analysis.get('data_intent'),
                    target_table=metadata.get('target_table'),
                    explanation=metadata.get('explanation', '从存储记录恢复'),
                    metadata=metadata,
                    analysis_timestamp=placeholder.analyzed_at or datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"获取存储SQL失败: {e}")
            return None
    
    async def _store_analysis_result(self, result: PlaceholderAnalysisResult):
        """存储分析结果到数据库"""
        
        try:
            from ....models.template_placeholder import TemplatePlaceholder
            
            if not self.db_session or not result.success:
                return
            
            placeholder = (
                self.db_session.query(TemplatePlaceholder)
                .filter(TemplatePlaceholder.id == result.placeholder_id)
                .first()
            )
            
            if placeholder:
                placeholder.generated_sql = result.generated_sql
                placeholder.analyzed_at = result.analysis_timestamp
                placeholder.parsing_metadata = result.metadata
                
                self.db_session.commit()
                
                logger.info(f"💾 分析结果已存储: {result.placeholder_id}")
            
        except Exception as e:
            logger.error(f"存储分析结果失败: {e}")
            if self.db_session:
                self.db_session.rollback()
    
    async def _analyze_with_llm(
        self,
        request: PlaceholderAnalysisRequest,
        schema_info: Dict[str, Any],
        context: AgentContext
    ) -> PlaceholderAnalysisResult:
        """使用LLM进行增强分析"""
        
        try:
            # 构建数据源上下文
            data_source_context = await self._build_data_source_context(
                request.data_source_id, schema_info
            )
            
            # 调用LLM增强分析器
            enhanced_result = await self.enhanced_analyzer.analyze_placeholder(
                placeholder_text=request.placeholder_text,
                data_source_context=data_source_context,
                template_context=request.template_context
            )
            
            # 转换为PlaceholderAnalysisResult格式
            analysis_result = PlaceholderAnalysisResult(
                success=True,
                placeholder_id=request.placeholder_id,
                generated_sql=enhanced_result.sql_query,
                confidence=enhanced_result.confidence,
                semantic_type=enhanced_result.primary_type,
                semantic_subtype=enhanced_result.sub_type,
                data_intent=enhanced_result.data_intent,
                target_table=enhanced_result.target_table,
                explanation=enhanced_result.explanation,
                suggestions=enhanced_result.suggestions,
                metadata={
                    'llm_enhanced': True,
                    'analyzer_type': 'llm',
                    'keywords': enhanced_result.keywords,
                    'target_columns': enhanced_result.target_columns,
                    'llm_metadata': enhanced_result.metadata
                }
            )
            
            # 存储结果到数据库（如果需要）
            if request.store_result:
                await self._store_analysis_result(analysis_result)
            
            # 更新上下文
            self.update_context(
                context, 'last_llm_analysis_result', 
                analysis_result.to_dict(), 
                ContextScope.TASK
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return PlaceholderAnalysisResult(
                success=False,
                placeholder_id=request.placeholder_id,
                error_message=f"LLM分析失败: {str(e)}",
                error_context={'llm_error': True}
            )
    
    async def _build_data_source_context(
        self, 
        data_source_id: str, 
        schema_info: Dict[str, Any]
    ) -> DataSourceContext:
        """构建数据源上下文信息"""
        
        try:
            from app import crud
            
            if not self.db_session:
                raise ValueError("数据库会话未初始化")
            
            # 获取数据源信息
            data_source = crud.data_source.get(self.db_session, id=data_source_id)
            if not data_source:
                raise ValueError(f"数据源 {data_source_id} 不存在")
            
            # 构建连接信息
            connection_info = {
                'source_type': data_source.source_type,
                'database': getattr(data_source, 'doris_database', ''),
                'hosts': getattr(data_source, 'doris_fe_hosts', []),
                'query_port': getattr(data_source, 'doris_query_port', 9030)
            }
            
            # 构建表信息列表
            tables_info = []
            for table_name in schema_info.get('tables', []):
                table_detail = schema_info.get('table_details', {}).get(table_name, {})
                
                table_info = {
                    'table_name': table_name,
                    'business_category': table_detail.get('business_category'),
                    'data_quality_score': table_detail.get('data_quality_score'),
                    'estimated_row_count': table_detail.get('estimated_row_count'),
                    'data_freshness': table_detail.get('data_freshness'),
                    'update_frequency': table_detail.get('update_frequency'),
                    'columns': table_detail.get('columns', [])
                }
                tables_info.append(table_info)
            
            return DataSourceContext(
                data_source_id=data_source_id,
                data_source_name=data_source.name,
                data_source_type=data_source.source_type,
                tables=tables_info,
                connection_info=connection_info
            )
            
        except Exception as e:
            logger.error(f"构建数据源上下文失败: {e}")
            # 返回最小化的上下文
            return DataSourceContext(
                data_source_id=data_source_id,
                data_source_name="unknown",
                data_source_type="unknown",
                tables=[],
                connection_info={}
            )


# 创建并注册Agent的工厂函数
def create_and_register_placeholder_sql_agent(
    db_session: Session = None, 
    user_id: str = None
) -> str:
    """创建并注册占位符SQL构建Agent"""
    
    # 创建Agent实例
    agent = PlaceholderSQLAgent(db_session=db_session, user_id=user_id)
    
    # 获取注册表并注册
    registry = get_agent_registry()
    agent_id = registry.register_agent(agent, priority=1, max_concurrent=3)
    
    logger.info(f"PlaceholderSQLAgent registered with ID: {agent_id}")
    return agent_id


# 便捷调用接口
class PlaceholderSQLAnalyzer:
    """占位符SQL分析器 - 提供简单的调用接口"""
    
    def __init__(self, db_session: Session = None, user_id: str = None):
        self.agent_id = create_and_register_placeholder_sql_agent(db_session, user_id)
        self.context_manager = get_context_manager()
        self.registry = get_agent_registry()
    
    async def analyze_placeholder(self, 
                                placeholder_id: str,
                                placeholder_text: str, 
                                data_source_id: str,
                                placeholder_type: str = "unknown",
                                template_id: str = None,
                                template_context: Dict[str, Any] = None,
                                force_reanalyze: bool = False) -> PlaceholderAnalysisResult:
        """分析单个占位符"""
        
        session_id = f"placeholder_analysis_{placeholder_id}_{datetime.now().timestamp()}"
        
        try:
            result = await self.registry.execute_capability(
                'analyze_placeholder_sql',
                session_id,
                {
                    'placeholder_id': placeholder_id,
                    'placeholder_text': placeholder_text,
                    'placeholder_type': placeholder_type,
                    'data_source_id': data_source_id,
                    'template_id': template_id,
                    'template_context': template_context,
                    'force_reanalyze': force_reanalyze
                }
            )
            
            result_data = result.get('result', {})
            return PlaceholderAnalysisResult(**result_data)
            
        except Exception as e:
            logger.error(f"占位符分析失败: {e}")
            return PlaceholderAnalysisResult(
                success=False,
                placeholder_id=placeholder_id,
                error_message=str(e)
            )
    
    async def check_stored_sql(self, placeholder_id: str) -> Dict[str, Any]:
        """检查是否已有存储的SQL"""
        
        session_id = f"check_sql_{placeholder_id}_{datetime.now().timestamp()}"
        
        try:
            result = await self.registry.execute_capability(
                'check_stored_sql',
                session_id,
                {'placeholder_id': placeholder_id}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"检查存储SQL失败: {e}")
            return {
                "has_sql": False,
                "sql": None,
                "error": str(e)
            }
    
    async def batch_analyze(self, requests: List[Dict[str, Any]]) -> List[PlaceholderAnalysisResult]:
        """批量分析占位符"""
        
        session_id = f"batch_analysis_{datetime.now().timestamp()}"
        
        try:
            result = await self.registry.execute_capability(
                'batch_analyze_placeholders',
                session_id,
                {'requests': requests}
            )
            
            results = result.get('results', [])
            return [PlaceholderAnalysisResult(**r) for r in results]
            
        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            return [PlaceholderAnalysisResult(
                success=False,
                placeholder_id="batch",
                error_message=str(e)
            )]

    async def analyze_and_execute(self, request) -> Any:
        """分析并执行占位符请求 - 兼容接口"""
        from ...domain.placeholder.models import AgentExecutionResult
        
        try:
            # 转换请求参数
            result = await self.analyze_placeholder(
                placeholder_id=request.placeholder_id,
                placeholder_text=request.placeholder_name, 
                data_source_id=request.data_source_id,
                placeholder_type=getattr(request, 'placeholder_type', 'unknown'),
                template_id=getattr(request, 'template_id', None),
                template_context=getattr(request, 'metadata', None),
                force_reanalyze=getattr(request, 'force_reanalyze', False)
            )
            
            # 转换结果格式
            if result.success:
                return AgentExecutionResult(
                    success=True,
                    raw_data=result.generated_sql,
                    formatted_value=f"SQL: {result.generated_sql[:100]}..." if result.generated_sql else "无SQL生成",
                    confidence=result.confidence,
                    execution_time_ms=0,  # 这里没有具体的执行时间
                    row_count=0,
                    metadata={
                        'semantic_type': result.semantic_type,
                        'target_table': result.target_table,
                        'explanation': result.explanation,
                        'analysis_metadata': result.metadata
                    },
                    error_message=None,
                    error_context={}
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    raw_data=None,
                    formatted_value="分析失败",
                    confidence=0.0,
                    execution_time_ms=0,
                    row_count=0,
                    metadata={},
                    error_message=result.error_message,
                    error_context=result.error_context or {}
                )
                
        except Exception as e:
            logger.error(f"analyze_and_execute 失败: {e}")
            return AgentExecutionResult(
                success=False,
                raw_data=None,
                formatted_value="执行异常",
                confidence=0.0,
                execution_time_ms=0,
                row_count=0,
                metadata={},
                error_message=str(e),
                error_context={'exception_type': type(e).__name__}
            )