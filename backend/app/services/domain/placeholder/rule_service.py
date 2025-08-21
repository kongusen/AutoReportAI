"""
模板规则层

负责规则引擎、模板生成、fallback处理
"""
import logging
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .models import (
    PlaceholderRequest, RuleGenerationResult, TemplateRuleServiceInterface,
    DataExecutionServiceInterface
)


class TemplateRuleService(TemplateRuleServiceInterface):
    """模板规则服务 - 只负责规则生成和执行"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rule_engine = RuleEngine(db_session)
        self.template_generator = TemplateGenerator(db_session)
        self.fallback_generator = FallbackGenerator()
        self.execution_service: Optional[DataExecutionServiceInterface] = None
        self.logger = logging.getLogger(__name__)
    
    def set_execution_service(self, execution_service: DataExecutionServiceInterface):
        """设置执行服务（依赖注入）"""
        self.execution_service = execution_service
    
    async def generate_and_execute(
        self, 
        request: PlaceholderRequest, 
        agent_error_context: Dict[str, Any]
    ) -> RuleGenerationResult:
        """规则生成和执行 - 不缓存结果"""
        
        try:
            self.logger.info(f"开始规则fallback处理: {request.placeholder_name}")
            
            # 1. 尝试基于错误上下文的智能规则生成
            rule_result = await self._generate_rule_sql(request, agent_error_context)
            if rule_result.success:
                execution_result = await self._execute_rule_sql(request, rule_result.sql, "intelligent_rule")
                if execution_result.success:
                    return RuleGenerationResult(
                        success=True,
                        sql=rule_result.sql,
                        formatted_value=execution_result.formatted_value,
                        execution_time_ms=execution_result.execution_time_ms,
                        rule_type="intelligent_rule",
                        metadata={
                            "source": "intelligent_rule", 
                            "rule_reasoning": rule_result.reasoning,
                            "agent_error": agent_error_context.get("stage", "unknown")
                        }
                    )
            
            # 2. 尝试基于占位符类型的模板生成
            template_result = await self._generate_template_sql(request)
            if template_result.success:
                execution_result = await self._execute_rule_sql(request, template_result.sql, "template")
                if execution_result.success:
                    return RuleGenerationResult(
                        success=True,
                        sql=template_result.sql,
                        formatted_value=execution_result.formatted_value,
                        execution_time_ms=execution_result.execution_time_ms,
                        rule_type="template",
                        metadata={
                            "source": "template", 
                            "template_type": template_result.template_type,
                            "placeholder_type": request.placeholder_type
                        }
                    )
            
            # 3. 尝试基于关键词的简单规则
            keyword_result = await self._generate_keyword_sql(request)
            if keyword_result.success:
                execution_result = await self._execute_rule_sql(request, keyword_result.sql, "keyword_rule")
                if execution_result.success:
                    return RuleGenerationResult(
                        success=True,
                        sql=keyword_result.sql,
                        formatted_value=execution_result.formatted_value,
                        execution_time_ms=execution_result.execution_time_ms,
                        rule_type="keyword_rule",
                        metadata={
                            "source": "keyword_rule",
                            "keywords": keyword_result.keywords
                        }
                    )
            
            # 4. 最终安全fallback
            fallback_result = await self._generate_fallback(request)
            return fallback_result
            
        except Exception as e:
            self.logger.error(f"规则处理异常: {e}", exc_info=True)
            return RuleGenerationResult(
                success=False,
                error_message=f"规则处理异常: {str(e)}"
            )
    
    async def _generate_rule_sql(self, request: PlaceholderRequest, error_context: Dict) -> Any:
        """基于错误上下文的智能规则生成"""
        return await self.rule_engine.generate_sql(request, error_context)
    
    async def _generate_template_sql(self, request: PlaceholderRequest) -> Any:
        """基于模板生成SQL"""
        return await self.template_generator.generate_sql(request)
    
    async def _generate_keyword_sql(self, request: PlaceholderRequest) -> Any:
        """基于关键词生成SQL"""
        return await self.rule_engine.generate_keyword_sql(request)
    
    async def _generate_fallback(self, request: PlaceholderRequest) -> RuleGenerationResult:
        """最终安全fallback"""
        return await self.fallback_generator.generate_safe_result(request)
    
    async def _execute_rule_sql(self, request: PlaceholderRequest, sql: str, rule_type: str) -> Any:
        """执行规则SQL"""
        try:
            if not self.execution_service:
                class ExecutionResult:
                    def __init__(self):
                        self.success = False
                        self.error_message = "执行服务未初始化"
                
                return ExecutionResult()
            
            self.logger.debug(f"执行{rule_type}SQL: {sql[:100]}...")
            execution_result = await self.execution_service.execute_sql(request.data_source_id, sql)
            
            if execution_result.success:
                self.logger.info(f"{rule_type}SQL执行成功: {request.placeholder_name}")
            else:
                self.logger.warning(f"{rule_type}SQL执行失败: {execution_result.error_message}")
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"执行{rule_type}SQL异常: {e}")
            
            class ExecutionResult:
                def __init__(self):
                    self.success = False
                    self.error_message = f"执行异常: {str(e)}"
            
            return ExecutionResult()


class RuleEngine:
    """规则引擎"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def generate_sql(self, request: PlaceholderRequest, error_context: Dict) -> Any:
        """基于规则和错误上下文生成SQL"""
        
        class RuleResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.reasoning = []
                self.error = None
        
        try:
            result = RuleResult()
            
            # 分析Agent失败的原因，选择合适的修复策略
            error_stage = error_context.get("stage", "unknown")
            
            if error_stage == "sql_execution":
                # SQL执行失败，尝试简化SQL
                result = await self._generate_simplified_sql(request, error_context)
            elif error_stage == "target_selection":
                # 目标选择失败，使用第一个可用表
                result = await self._generate_first_table_sql(request, error_context)
            elif error_stage == "sql_validation":
                # SQL验证失败，使用安全的模板
                result = await self._generate_safe_template_sql(request)
            else:
                # 其他情况，使用通用规则
                result = await self._generate_generic_sql(request)
            
            if result.success:
                result.reasoning.append(f"基于错误阶段 '{error_stage}' 生成的修复SQL")
            
            return result
            
        except Exception as e:
            result = RuleResult()
            result.error = f"规则生成异常: {str(e)}"
            self.logger.error(f"规则生成异常: {e}")
            return result
    
    async def generate_keyword_sql(self, request: PlaceholderRequest) -> Any:
        """基于关键词生成SQL"""
        
        class KeywordResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.keywords = []
                self.error = None
        
        try:
            result = KeywordResult()
            
            # 从占位符名称中提取关键词
            placeholder_name = request.placeholder_name.lower()
            
            # 获取可用表
            available_tables = await self._get_available_tables(request.data_source_id)
            if not available_tables:
                result.error = "没有可用的数据表"
                return result
            
            # 关键词匹配表名
            target_table = None
            matched_keywords = []
            
            # 定义关键词映射规则
            keyword_table_mapping = {
                "投诉": ["complain", "complaint"],
                "用户": ["user", "customer"],
                "订单": ["order", "trade"],
                "统计": ["stat", "count", "summary"],
                "分析": ["analysis", "report"],
                "数据": ["data", "info"]
            }
            
            for keyword, table_patterns in keyword_table_mapping.items():
                if keyword in placeholder_name:
                    matched_keywords.append(keyword)
                    for pattern in table_patterns:
                        for table in available_tables:
                            if pattern in table.lower():
                                target_table = table
                                break
                        if target_table:
                            break
                    if target_table:
                        break
            
            # 如果没有匹配到特定表，使用第一个可用表
            if not target_table:
                target_table = available_tables[0]
                matched_keywords.append("通用")
            
            # 生成基础SQL
            if "统计" in placeholder_name or "数量" in placeholder_name or "个数" in placeholder_name:
                sql = f"SELECT COUNT(*) as count FROM {target_table}"
            elif "总和" in placeholder_name or "合计" in placeholder_name:
                sql = f"SELECT COUNT(*) as total FROM {target_table}"
            elif "平均" in placeholder_name:
                sql = f"SELECT COUNT(*) as avg_count FROM {target_table}"
            else:
                sql = f"SELECT COUNT(*) as count FROM {target_table}"
            
            # 添加LIMIT
            sql += " LIMIT 1000"
            
            result.success = True
            result.sql = sql
            result.keywords = matched_keywords
            
            return result
            
        except Exception as e:
            result = KeywordResult()
            result.error = f"关键词规则生成异常: {str(e)}"
            self.logger.error(f"关键词规则生成异常: {e}")
            return result
    
    async def _generate_simplified_sql(self, request: PlaceholderRequest, error_context: Dict):
        """生成简化的SQL"""
        class RuleResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.reasoning = []
        
        try:
            result = RuleResult()
            
            # 从错误上下文中获取失败的SQL和表名
            failed_sql = error_context.get("sql", "")
            target_table = error_context.get("target_table", "")
            
            if target_table:
                # 生成最简单的COUNT查询
                sql = f"SELECT COUNT(*) as count FROM {target_table} LIMIT 100"
                result.success = True
                result.sql = sql
                result.reasoning.append("简化为基础COUNT查询避免复杂操作")
            
            return result
            
        except Exception as e:
            result = RuleResult()
            result.reasoning.append(f"简化SQL生成失败: {str(e)}")
            return result
    
    async def _generate_first_table_sql(self, request: PlaceholderRequest, error_context: Dict):
        """使用第一个可用表生成SQL"""
        class RuleResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.reasoning = []
        
        try:
            result = RuleResult()
            
            available_tables = await self._get_available_tables(request.data_source_id)
            if available_tables:
                table = available_tables[0]
                sql = f"SELECT COUNT(*) as count FROM {table} LIMIT 100"
                result.success = True
                result.sql = sql
                result.reasoning.append(f"使用第一个可用表: {table}")
            
            return result
            
        except Exception as e:
            result = RuleResult()
            result.reasoning.append(f"第一表SQL生成失败: {str(e)}")
            return result
    
    async def _generate_safe_template_sql(self, request: PlaceholderRequest):
        """生成安全的模板SQL"""
        class RuleResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.reasoning = []
        
        try:
            result = RuleResult()
            
            available_tables = await self._get_available_tables(request.data_source_id)
            if available_tables:
                table = available_tables[0]
                sql = f"SELECT COUNT(*) as count FROM {table} LIMIT 10"
                result.success = True
                result.sql = sql
                result.reasoning.append("使用安全的计数模板")
            
            return result
            
        except Exception as e:
            result = RuleResult()
            result.reasoning.append(f"安全模板SQL生成失败: {str(e)}")
            return result
    
    async def _generate_generic_sql(self, request: PlaceholderRequest):
        """生成通用SQL"""
        class RuleResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.reasoning = []
        
        try:
            result = RuleResult()
            
            available_tables = await self._get_available_tables(request.data_source_id)
            if available_tables:
                table = available_tables[0]
                sql = f"SELECT COUNT(*) as count FROM {table} LIMIT 50"
                result.success = True
                result.sql = sql
                result.reasoning.append("使用通用计数规则")
            
            return result
            
        except Exception as e:
            result = RuleResult()
            result.reasoning.append(f"通用SQL生成失败: {str(e)}")
            return result
    
    async def _get_available_tables(self, data_source_id: str) -> List[str]:
        """获取可用表列表"""
        try:
            from app.services.data.schemas.schema_query_service import SchemaQueryService
            
            schema_service = SchemaQueryService(self.db)
            table_schemas = schema_service.get_table_schemas(data_source_id)
            
            return [schema.table_name for schema in table_schemas] if table_schemas else []
            
        except Exception as e:
            self.logger.error(f"获取可用表失败: {e}")
            return []


class TemplateGenerator:
    """模板生成器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def generate_sql(self, request: PlaceholderRequest) -> Any:
        """基于占位符类型生成模板SQL"""
        
        class TemplateResult:
            def __init__(self):
                self.success = False
                self.sql = None
                self.template_type = None
                self.error = None
        
        try:
            result = TemplateResult()
            
            # 获取可用表
            available_tables = await self._get_available_tables(request.data_source_id)
            if not available_tables:
                result.error = "没有可用的数据表"
                return result
            
            target_table = available_tables[0]
            placeholder_type = request.placeholder_type.lower()
            placeholder_name = request.placeholder_name.lower()
            
            # 根据占位符类型选择模板
            if placeholder_type == "statistic" or "统计" in placeholder_name:
                result.template_type = "statistic"
                if "占比" in placeholder_name or "比例" in placeholder_name:
                    sql = f"SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {target_table}) as percentage FROM {target_table}"
                elif "去重" in placeholder_name or "distinct" in placeholder_name:
                    sql = f"SELECT COUNT(DISTINCT id) as distinct_count FROM {target_table}"
                else:
                    sql = f"SELECT COUNT(*) as count FROM {target_table}"
                    
            elif placeholder_type == "metric" or "指标" in placeholder_name:
                result.template_type = "metric"
                sql = f"SELECT COUNT(*) as metric_value FROM {target_table}"
                
            elif placeholder_type == "summary" or "汇总" in placeholder_name:
                result.template_type = "summary"
                sql = f"SELECT COUNT(*) as summary_count FROM {target_table}"
                
            else:
                result.template_type = "default"
                sql = f"SELECT COUNT(*) as value FROM {target_table}"
            
            # 添加LIMIT
            sql += " LIMIT 500"
            
            result.success = True
            result.sql = sql
            
            return result
            
        except Exception as e:
            result = TemplateResult()
            result.error = f"模板生成异常: {str(e)}"
            self.logger.error(f"模板生成异常: {e}")
            return result
    
    async def _get_available_tables(self, data_source_id: str) -> List[str]:
        """获取可用表列表"""
        try:
            from app.services.data.schemas.schema_query_service import SchemaQueryService
            
            schema_service = SchemaQueryService(self.db)
            table_schemas = schema_service.get_table_schemas(data_source_id)
            
            return [schema.table_name for schema in table_schemas] if table_schemas else []
            
        except Exception as e:
            self.logger.error(f"获取可用表失败: {e}")
            return []


class FallbackGenerator:
    """Fallback生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_safe_result(self, request: PlaceholderRequest) -> RuleGenerationResult:
        """生成安全的fallback结果"""
        try:
            self.logger.warning(f"使用最终fallback: {request.placeholder_name}")
            
            # 根据占位符类型返回不同的默认值
            placeholder_name = request.placeholder_name.lower()
            
            if "数量" in placeholder_name or "个数" in placeholder_name or "count" in placeholder_name:
                fallback_value = "0"
            elif "占比" in placeholder_name or "比例" in placeholder_name or "率" in placeholder_name:
                fallback_value = "0%"
            elif "金额" in placeholder_name or "费用" in placeholder_name or "价格" in placeholder_name:
                fallback_value = "0.00元"
            elif "时间" in placeholder_name or "日期" in placeholder_name:
                fallback_value = "暂无数据"
            else:
                fallback_value = "数据暂不可用"
            
            return RuleGenerationResult(
                success=True,
                formatted_value=fallback_value,
                execution_time_ms=0,
                rule_type="safe_fallback",
                metadata={
                    "source": "safe_fallback", 
                    "reason": "all_methods_failed",
                    "placeholder_type": request.placeholder_type,
                    "fallback_strategy": "type_based_default"
                }
            )
            
        except Exception as e:
            self.logger.error(f"安全fallback失败: {e}")
            return RuleGenerationResult(
                success=True,
                formatted_value="数据获取失败",
                execution_time_ms=0,
                rule_type="emergency_fallback",
                metadata={"source": "emergency_fallback", "error": str(e)}
            )