"""
Agent分析层

负责AI分析、SQL生成、结果验证、SQL执行
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from .models import (
    PlaceholderRequest, AgentAnalysisResult, AgentExecutionResult, 
    SchemaInfo, AgentAnalysisServiceInterface, DataExecutionServiceInterface
)


class AgentAnalysisService(AgentAnalysisServiceInterface):
    """Agent分析服务 - 只负责Agent相关的分析和执行"""
    
    def __init__(self, db_session: Session, user_id: str):
        self.db = db_session
        self.user_id = user_id
        self.schema_analyzer = SchemaAnalyzer(db_session)
        self.ai_processor = AIProcessor(user_id)
        self.sql_generator = SQLGenerator()
        self.sql_validator = SQLValidator()
        self.execution_service: Optional[DataExecutionServiceInterface] = None
        self.logger = logging.getLogger(__name__)
    
    def set_execution_service(self, execution_service: DataExecutionServiceInterface):
        """设置执行服务（依赖注入）"""
        self.execution_service = execution_service
    
    async def analyze_and_execute(self, request: PlaceholderRequest) -> AgentExecutionResult:
        """完整的Agent分析和执行流程"""
        
        try:
            # 1. 分析阶段
            self.logger.debug(f"开始Agent分析: {request.placeholder_name}")
            analysis_result = await self._analyze(request)
            
            if not analysis_result.success:
                return AgentExecutionResult(
                    success=False,
                    error_message=analysis_result.error_message,
                    error_context=analysis_result.error_context
                )
            
            # 2. 执行阶段
            self.logger.debug(f"开始执行Agent SQL: {request.placeholder_name}")
            execution_result = await self._execute(request, analysis_result)
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Agent分析和执行异常: {str(e)}", exc_info=True)
            return AgentExecutionResult(
                success=False,
                error_message=f"Agent处理异常: {str(e)}",
                error_context={"stage": "exception", "exception": str(e)}
            )
    
    async def _analyze(self, request: PlaceholderRequest) -> AgentAnalysisResult:
        """Agent分析阶段"""
        try:
            # 1. 获取Schema信息
            schema_info = await self.schema_analyzer.get_schema_info(request.data_source_id)
            if not schema_info:
                return AgentAnalysisResult(
                    success=False,
                    error_message="无法获取数据源schema信息",
                    error_context={"stage": "schema_analysis", "data_source_id": request.data_source_id}
                )
            
            # 2. AI处理
            ai_result = await self.ai_processor.analyze_placeholder(
                request.placeholder_name, 
                request.placeholder_type,
                schema_info,
                request.metadata
            )
            
            if not ai_result.success:
                return AgentAnalysisResult(
                    success=False,
                    error_message=f"AI分析失败: {ai_result.error}",
                    error_context={
                        "stage": "ai_processing", 
                        "ai_error": ai_result.error,
                        "placeholder_name": request.placeholder_name
                    }
                )
            
            # 3. 目标选择
            target_info = await self._select_target_table(ai_result, schema_info)
            if not target_info.success:
                return AgentAnalysisResult(
                    success=False,
                    error_message=f"目标选择失败: {target_info.error}",
                    error_context={
                        "stage": "target_selection",
                        "ai_result": ai_result.analysis_data,
                        "available_tables": schema_info.tables
                    }
                )
            
            # 4. SQL生成
            sql_result = await self.sql_generator.generate_sql(
                ai_result, target_info, schema_info
            )
            
            if not sql_result.success:
                return AgentAnalysisResult(
                    success=False,
                    error_message=f"SQL生成失败: {sql_result.error}",
                    error_context={
                        "stage": "sql_generation",
                        "ai_result": ai_result.analysis_data,
                        "target_info": target_info.target_table
                    }
                )
            
            # 5. SQL验证
            validation_result = await self.sql_validator.validate_sql(
                sql_result.sql, schema_info
            )
            
            if not validation_result.valid:
                return AgentAnalysisResult(
                    success=False,
                    error_message=f"SQL验证失败: {validation_result.error}",
                    error_context={
                        "stage": "sql_validation", 
                        "sql": sql_result.sql,
                        "validation_error": validation_result.error
                    }
                )
            
            return AgentAnalysisResult(
                success=True,
                sql=sql_result.sql,
                confidence=ai_result.confidence,
                reasoning=ai_result.reasoning,
                target_table=target_info.target_table,
                target_fields=target_info.fields,
                metadata={
                    "ai_analysis": ai_result.analysis_data,
                    "target_info": target_info.__dict__,
                    "sql_generation": sql_result.__dict__
                }
            )
            
        except Exception as e:
            self.logger.error(f"Agent分析异常: {e}", exc_info=True)
            return AgentAnalysisResult(
                success=False,
                error_message=f"Agent分析异常: {str(e)}",
                error_context={"stage": "analysis_exception", "exception": str(e)}
            )
    
    async def _execute(self, request: PlaceholderRequest, analysis: AgentAnalysisResult) -> AgentExecutionResult:
        """Agent执行阶段"""
        try:
            if not self.execution_service:
                return AgentExecutionResult(
                    success=False,
                    error_message="执行服务未初始化",
                    error_context={"stage": "execution_setup"}
                )
            
            # 执行SQL
            execution_result = await self.execution_service.execute_sql(
                request.data_source_id,
                analysis.sql
            )
            
            if execution_result.success:
                return AgentExecutionResult(
                    success=True,
                    formatted_value=execution_result.formatted_value,
                    execution_time_ms=execution_result.execution_time_ms,
                    confidence=analysis.confidence,
                    raw_data=execution_result.raw_data,
                    row_count=execution_result.row_count,
                    metadata={
                        "sql": analysis.sql,
                        "target_table": analysis.target_table,
                        "target_fields": analysis.target_fields,
                        "reasoning": analysis.reasoning,
                        "analysis_metadata": analysis.metadata
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"SQL执行失败: {execution_result.error_message}",
                    error_context={
                        "stage": "sql_execution",
                        "sql": analysis.sql,
                        "execution_error": execution_result.error_message,
                        "target_table": analysis.target_table
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Agent执行异常: {e}", exc_info=True)
            return AgentExecutionResult(
                success=False,
                error_message=f"Agent执行异常: {str(e)}",
                error_context={"stage": "execution_exception", "exception": str(e)}
            )
    
    async def _select_target_table(self, ai_result, schema_info: SchemaInfo):
        """选择目标表"""
        # 简化实现 - 使用AI推荐的表或第一个可用表
        class TargetInfo:
            def __init__(self):
                self.success = False
                self.target_table = None
                self.fields = []
                self.error = None
        
        target_info = TargetInfo()
        
        try:
            # 从AI结果中获取推荐的表
            recommended_table = getattr(ai_result, 'target_table', None)
            
            if recommended_table and recommended_table in schema_info.tables:
                target_info.success = True
                target_info.target_table = recommended_table
                target_info.fields = getattr(ai_result, 'target_fields', [])
            elif schema_info.tables:
                # 使用第一个可用表
                target_info.success = True
                target_info.target_table = schema_info.tables[0]
                target_info.fields = []
                self.logger.warning(f"使用备用表: {target_info.target_table}")
            else:
                target_info.error = "没有可用的数据表"
            
            return target_info
            
        except Exception as e:
            target_info.error = f"目标选择异常: {str(e)}"
            return target_info


class SchemaAnalyzer:
    """Schema分析器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def get_schema_info(self, data_source_id: str) -> Optional[SchemaInfo]:
        """获取Schema信息"""
        try:
            # 从缓存的表结构信息中获取
            from app.services.data.schemas.schema_query_service import SchemaQueryService
            
            schema_service = SchemaQueryService(self.db)
            table_schemas = schema_service.get_table_schemas(data_source_id)
            
            if not table_schemas:
                self.logger.warning(f"数据源 {data_source_id} 没有缓存的表结构信息")
                return None
            
            # 构建表结构详情
            tables = []
            table_details = {}
            
            for table_schema in table_schemas:
                table_name = table_schema.table_name
                tables.append(table_name)
                
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
                
                table_details[table_name] = {
                    "columns": column_details,
                    "business_category": table_schema.business_category,
                    "data_freshness": table_schema.data_freshness,
                    "update_frequency": table_schema.update_frequency,
                    "estimated_row_count": table_schema.estimated_row_count,
                    "data_quality_score": table_schema.data_quality_score
                }
            
            return SchemaInfo(
                data_source_id=data_source_id,
                tables=tables,
                table_details=table_details,
                metadata={
                    "total_tables": len(tables),
                    "total_columns": sum(len(details["columns"]) for details in table_details.values()),
                    "business_categories": list(set([t.business_category for t in table_schemas if t.business_category]))
                }
            )
            
        except Exception as e:
            self.logger.error(f"获取Schema信息失败: {e}")
            return None


class AIProcessor:
    """AI处理器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
    
    async def analyze_placeholder(
        self, 
        placeholder_name: str, 
        placeholder_type: str, 
        schema_info: SchemaInfo,
        metadata: Dict[str, Any]
    ):
        """AI分析占位符"""
        
        class AIResult:
            def __init__(self):
                self.success = False
                self.confidence = 0.0
                self.reasoning = []
                self.analysis_data = {}
                self.target_table = None
                self.target_fields = []
                self.error = None
        
        try:
            # 使用现有的MultiDatabaseAgent进行分析
            from app.services.agents.multi_database_agent import MultiDatabaseAgent
            
            agent = MultiDatabaseAgent(db_session=self.db_session, user_id=self.user_id)
            
            # 构建Agent输入
            agent_input = {
                "placeholder_name": placeholder_name,
                "placeholder_type": placeholder_type,
                "data_source": {
                    "id": schema_info.data_source_id,
                    "name": f"DataSource_{schema_info.data_source_id}",
                    "source_type": "doris"  # 默认类型，可以从数据源配置中获取
                }
            }
            
            # 执行分析（不包含执行步骤）
            analysis_result = await agent.analyze_placeholder_requirements(agent_input)
            
            ai_result = AIResult()
            
            if analysis_result.get("success"):
                ai_result.success = True
                ai_result.confidence = analysis_result.get("confidence_score", 0.8)
                ai_result.reasoning = analysis_result.get("reasoning", [])
                ai_result.target_table = analysis_result.get("target_table")
                ai_result.target_fields = analysis_result.get("required_fields", [])
                ai_result.analysis_data = {
                    "intent": analysis_result.get("intent", "statistical"),
                    "data_operation": analysis_result.get("data_operation", "count"),
                    "business_domain": analysis_result.get("business_domain", ""),
                    "target_metrics": analysis_result.get("target_metrics", []),
                    "optimizations": analysis_result.get("optimizations", [])
                }
            else:
                ai_result.error = analysis_result.get("error", "AI分析失败")
            
            return ai_result
            
        except Exception as e:
            ai_result = AIResult()
            ai_result.error = f"AI处理异常: {str(e)}"
            self.logger.error(f"AI处理异常: {e}", exc_info=True)
            return ai_result
    
    @property 
    def db_session(self):
        """获取数据库会话 - 临时解决方案"""
        from app.db.session import SessionLocal
        return SessionLocal()


class SQLGenerator:
    """SQL生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_sql(self, ai_result, target_info, schema_info: SchemaInfo):
        """生成SQL"""
        
        class SQLResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.error = None
        
        try:
            sql_result = SQLResult()
            
            # 使用MultiDatabaseAgent的SQL生成逻辑
            from app.services.agents.multi_database_agent import MultiDatabaseAgent
            
            # 基于AI分析结果生成SQL
            data_operation = ai_result.analysis_data.get("data_operation", "count")
            target_table = target_info.target_table
            target_fields = target_info.fields
            
            # 简化的SQL生成逻辑
            if data_operation == "count":
                sql = f"SELECT COUNT(*) as total_count FROM {target_table}"
            elif data_operation == "count_distinct" and target_fields:
                field = target_fields[0]
                sql = f"SELECT COUNT(DISTINCT {field}) as distinct_count FROM {target_table}"
            elif data_operation == "sum" and target_fields:
                field = target_fields[0]
                sql = f"SELECT SUM({field}) as total_sum FROM {target_table}"
            elif data_operation == "avg" and target_fields:
                field = target_fields[0]
                sql = f"SELECT AVG({field}) as avg_value FROM {target_table}"
            else:
                sql = f"SELECT COUNT(*) as total_count FROM {target_table}"
            
            # 添加默认LIMIT
            sql += " LIMIT 1000"
            
            sql_result.success = True
            sql_result.sql = sql
            
            return sql_result
            
        except Exception as e:
            sql_result = SQLResult()
            sql_result.error = f"SQL生成异常: {str(e)}"
            self.logger.error(f"SQL生成异常: {e}")
            return sql_result


class SQLValidator:
    """SQL验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def validate_sql(self, sql: str, schema_info: SchemaInfo):
        """验证SQL"""
        
        class ValidationResult:
            def __init__(self):
                self.valid = False
                self.error = None
        
        try:
            result = ValidationResult()
            
            if not sql:
                result.error = "SQL为空"
                return result
            
            sql_upper = sql.upper()
            
            # 基本语法检查
            if not sql_upper.startswith('SELECT'):
                result.error = "SQL必须以SELECT开始"
                return result
            
            if 'FROM' not in sql_upper:
                result.error = "SQL缺少FROM子句"
                return result
            
            # 检查危险关键词
            dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE', 'INSERT']
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    result.error = f"SQL包含危险关键词: {keyword}"
                    return result
            
            # 检查表名是否存在
            for table in schema_info.tables:
                if table in sql:
                    result.valid = True
                    return result
            
            result.error = "SQL中没有找到有效的表名"
            return result
            
        except Exception as e:
            result = ValidationResult()
            result.error = f"SQL验证异常: {str(e)}"
            self.logger.error(f"SQL验证异常: {e}")
            return result