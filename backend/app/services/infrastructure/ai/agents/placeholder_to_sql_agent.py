"""
占位符→SQL转换Agent

基于AutoReportAI Agent设计的核心功能：
1. 占位符→SQL转换: 基于数据源表结构和时间上下文，智能生成准确SQL
2. 时间上下文分析 → 占位符解析 → 数据源Schema获取 → SQL生成 → SQL验证纠错 → 结果存储

特性：
- 智能模型选择：根据步骤复杂度自动选择合适模型
- SQL智能纠错：多轮纠错机制，支持语法错误和结果不符预期的修复
- 时间上下文处理：专门分析任务时间范围，生成准确时间过滤条件
- 多上下文融合：数据源上下文 + 任务上下文 + 模板上下文 + 时间上下文
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re

from ..llm.step_based_model_selector import (
    StepBasedModelSelector, 
    StepContext, 
    ProcessingStep,
    TaskComplexity,
    create_step_based_model_selector
)
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderContext:
    """占位符上下文"""
    placeholder_name: str
    placeholder_description: str
    placeholder_type: str              # 'metric', 'dimension', 'filter', 'chart'
    expected_data_type: str           # 'number', 'string', 'date', 'list'
    current_value: Optional[str] = None
    is_empty: bool = True
    last_updated: Optional[datetime] = None


@dataclass
class TimeContext:
    """时间上下文"""
    report_start_date: Optional[datetime] = None
    report_end_date: Optional[datetime] = None
    time_granularity: str = "day"     # 'hour', 'day', 'week', 'month', 'year'
    relative_time: Optional[str] = None  # 'last_week', 'last_month', 'ytd', etc.
    time_zone: str = "UTC"
    auto_detected: bool = False       # 是否自动检测的时间范围


@dataclass
class DataSourceContext:
    """数据源上下文"""
    source_id: str
    source_type: str                  # 'doris', 'mysql', 'postgresql', etc.
    database_name: str
    available_tables: List[str]
    table_schemas: Dict[str, List[Dict[str, Any]]]  # table_name -> columns
    connection_info: Dict[str, Any]


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    task_name: str
    task_description: str
    business_domain: str              # 'sales', 'marketing', 'finance', etc.
    report_type: str                  # 'dashboard', 'report', 'alert', etc.
    priority: str = "medium"          # 'low', 'medium', 'high', 'critical'


@dataclass
class SqlGenerationResult:
    """SQL生成结果"""
    sql_query: str
    explanation: str
    confidence_score: float           # 0.0 - 1.0
    used_tables: List[str]
    used_columns: List[str]
    time_filters: List[str]
    validation_errors: List[str] = None
    correction_attempts: int = 0


class PlaceholderToSqlAgent:
    """占位符→SQL转换Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model_selector = create_step_based_model_selector()
        self.correction_history: Dict[str, List[str]] = {}  # placeholder -> corrections
        
    async def convert_placeholder_to_sql(
        self,
        placeholder_context: PlaceholderContext,
        data_source_context: DataSourceContext,
        task_context: TaskContext,
        time_context: Optional[TimeContext] = None
    ) -> SqlGenerationResult:
        """
        将占位符转换为SQL查询
        
        主要流程：
        1. 时间上下文分析
        2. 占位符解析
        3. 数据源Schema获取
        4. SQL生成
        5. SQL验证纠错
        """
        try:
            logger.info(f"开始转换占位符 {placeholder_context.placeholder_name} 为SQL")
            
            # 步骤1: 时间上下文分析
            analyzed_time_context = await self._analyze_time_context(
                time_context or TimeContext(),
                task_context
            )
            
            # 步骤2: 占位符解析
            parsed_placeholder = await self._parse_placeholder(
                placeholder_context,
                task_context
            )
            
            # 步骤3: 数据源Schema获取和分析
            schema_analysis = await self._analyze_data_source_schema(
                data_source_context,
                parsed_placeholder,
                analyzed_time_context
            )
            
            # 步骤4: SQL生成
            sql_result = await self._generate_sql(
                parsed_placeholder,
                schema_analysis,
                analyzed_time_context,
                task_context
            )
            
            # 步骤5: SQL验证和纠错
            validated_result = await self._validate_and_correct_sql(
                sql_result,
                data_source_context,
                placeholder_context
            )
            
            logger.info(f"占位符 {placeholder_context.placeholder_name} 转换完成")
            return validated_result
            
        except Exception as e:
            logger.error(f"占位符转换失败: {e}")
            return SqlGenerationResult(
                sql_query="",
                explanation=f"转换失败: {str(e)}",
                confidence_score=0.0,
                used_tables=[],
                used_columns=[],
                time_filters=[],
                validation_errors=[str(e)]
            )
    
    async def _analyze_time_context(
        self,
        time_context: TimeContext,
        task_context: TaskContext
    ) -> TimeContext:
        """分析和增强时间上下文"""
        
        step_context = StepContext(
            step=ProcessingStep.TIME_CONTEXT_ANALYSIS,
            task_description=f"分析任务 {task_context.task_name} 的时间上下文",
            data_complexity="medium"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请分析以下任务的时间上下文需求：
        
        任务信息：
        - 任务名称: {task_context.task_name}
        - 任务描述: {task_context.task_description}
        - 业务领域: {task_context.business_domain}
        - 报告类型: {task_context.report_type}
        
        当前时间上下文：
        - 开始日期: {time_context.report_start_date}
        - 结束日期: {time_context.report_end_date}
        - 时间粒度: {time_context.time_granularity}
        - 相对时间: {time_context.relative_time}
        
        请分析并补充完整的时间上下文，包括：
        1. 如果缺少时间范围，根据任务类型推断合理的时间范围
        2. 确定最适合的时间粒度
        3. 生成时间过滤条件的SQL片段建议
        
        返回JSON格式，包含：
        - start_date: 开始日期 (YYYY-MM-DD)
        - end_date: 结束日期 (YYYY-MM-DD)  
        - granularity: 时间粒度
        - sql_time_filter: 时间过滤SQL片段
        - reasoning: 推理过程
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="time_context_analysis",
                complexity=model_selection.complexity.value
            )
            
            # 解析响应
            analysis_result = json.loads(response)
            
            # 更新时间上下文
            if analysis_result.get("start_date"):
                time_context.report_start_date = datetime.fromisoformat(analysis_result["start_date"])
            if analysis_result.get("end_date"):  
                time_context.report_end_date = datetime.fromisoformat(analysis_result["end_date"])
            if analysis_result.get("granularity"):
                time_context.time_granularity = analysis_result["granularity"]
                
            time_context.auto_detected = True
            
            logger.info(f"时间上下文分析完成: {analysis_result.get('reasoning', '无推理信息')}")
            
        except Exception as e:
            logger.error(f"时间上下文分析失败: {e}")
            # 使用默认时间范围
            if not time_context.report_start_date:
                time_context.report_start_date = datetime.now() - timedelta(days=30)
            if not time_context.report_end_date:
                time_context.report_end_date = datetime.now()
                
        return time_context
    
    async def _parse_placeholder(
        self,
        placeholder_context: PlaceholderContext,
        task_context: TaskContext
    ) -> Dict[str, Any]:
        """解析占位符的语义和需求"""
        
        step_context = StepContext(
            step=ProcessingStep.PLACEHOLDER_ANALYSIS,
            task_description=f"解析占位符 {placeholder_context.placeholder_name}",
            data_complexity="medium"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请解析以下占位符的语义和SQL需求：
        
        占位符信息：
        - 名称: {placeholder_context.placeholder_name}
        - 描述: {placeholder_context.placeholder_description}  
        - 类型: {placeholder_context.placeholder_type}
        - 期望数据类型: {placeholder_context.expected_data_type}
        - 当前值: {placeholder_context.current_value}
        
        任务上下文：
        - 业务领域: {task_context.business_domain}
        - 报告类型: {task_context.report_type}
        - 任务描述: {task_context.task_description}
        
        请分析占位符的语义含义和SQL生成需求，返回JSON格式：
        - semantic_type: 语义类型 (如 'count', 'sum', 'avg', 'ratio', 'trend')
        - aggregation_function: 聚合函数需求
        - filter_requirements: 过滤条件需求
        - grouping_requirements: 分组需求
        - join_requirements: 关联表需求
        - calculation_logic: 计算逻辑描述
        - business_rules: 业务规则
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="placeholder_analysis",
                complexity=model_selection.complexity.value
            )
            
            parsed_result = json.loads(response)
            logger.info(f"占位符解析完成: {placeholder_context.placeholder_name}")
            return parsed_result
            
        except Exception as e:
            logger.error(f"占位符解析失败: {e}")
            return {
                "semantic_type": "unknown",
                "aggregation_function": "COUNT",
                "filter_requirements": [],
                "grouping_requirements": [],
                "join_requirements": [],
                "calculation_logic": placeholder_context.placeholder_description,
                "business_rules": []
            }
    
    async def _analyze_data_source_schema(
        self,
        data_source_context: DataSourceContext,
        parsed_placeholder: Dict[str, Any],
        time_context: TimeContext
    ) -> Dict[str, Any]:
        """分析数据源Schema并匹配最佳表和字段"""
        
        step_context = StepContext(
            step=ProcessingStep.DATA_SOURCE_ANALYSIS,
            task_description="分析数据源Schema匹配",
            data_complexity="medium"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        # 构建schema信息
        schema_info = ""
        for table_name, columns in data_source_context.table_schemas.items():
            schema_info += f"\n表 {table_name}:\n"
            for col in columns:
                schema_info += f"  - {col.get('name', '')}: {col.get('type', '')} ({col.get('comment', 'no comment')})\n"
        
        prompt = f"""
        请分析数据源Schema并找到最适合生成SQL的表和字段：
        
        数据源信息：
        - 数据源类型: {data_source_context.source_type}
        - 数据库: {data_source_context.database_name}
        - 可用表: {', '.join(data_source_context.available_tables)}
        
        Schema详情：{schema_info}
        
        占位符需求：
        - 语义类型: {parsed_placeholder.get('semantic_type')}
        - 聚合函数: {parsed_placeholder.get('aggregation_function')}
        - 过滤需求: {parsed_placeholder.get('filter_requirements')}
        - 分组需求: {parsed_placeholder.get('grouping_requirements')}
        - 关联需求: {parsed_placeholder.get('join_requirements')}
        
        时间上下文：
        - 时间范围: {time_context.report_start_date} 到 {time_context.report_end_date}
        - 时间粒度: {time_context.time_granularity}
        
        请选择最合适的表和字段，返回JSON格式：
        - primary_table: 主表名
        - primary_columns: 主要字段列表
        - join_tables: 需要关联的表 
        - time_column: 时间字段
        - filter_columns: 过滤字段
        - groupby_columns: 分组字段
        - schema_confidence: 匹配信心度 (0.0-1.0)
        - reasoning: 选择理由
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis", 
                task_type="schema_analysis",
                complexity=model_selection.complexity.value
            )
            
            schema_analysis = json.loads(response)
            logger.info(f"Schema分析完成，主表: {schema_analysis.get('primary_table')}")
            return schema_analysis
            
        except Exception as e:
            logger.error(f"Schema分析失败: {e}")
            # 降级处理：选择第一个表
            first_table = data_source_context.available_tables[0] if data_source_context.available_tables else "unknown_table"
            return {
                "primary_table": first_table,
                "primary_columns": ["*"],
                "join_tables": [],
                "time_column": "created_at",
                "filter_columns": [],
                "groupby_columns": [],
                "schema_confidence": 0.3,
                "reasoning": f"Schema分析失败，降级使用表 {first_table}"
            }
    
    async def _generate_sql(
        self,
        parsed_placeholder: Dict[str, Any],
        schema_analysis: Dict[str, Any],
        time_context: TimeContext,
        task_context: TaskContext
    ) -> SqlGenerationResult:
        """生成SQL查询"""
        
        step_context = StepContext(
            step=ProcessingStep.SQL_GENERATION,
            task_description=f"为任务 {task_context.task_name} 生成SQL",
            data_complexity="high"  # SQL生成是高复杂度任务
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请根据以下信息生成准确的SQL查询：
        
        占位符语义：
        - 类型: {parsed_placeholder.get('semantic_type')}
        - 聚合函数: {parsed_placeholder.get('aggregation_function')}
        - 计算逻辑: {parsed_placeholder.get('calculation_logic')}
        - 业务规则: {parsed_placeholder.get('business_rules')}
        
        Schema分析：
        - 主表: {schema_analysis.get('primary_table')}
        - 主要字段: {schema_analysis.get('primary_columns')}
        - 关联表: {schema_analysis.get('join_tables')}
        - 时间字段: {schema_analysis.get('time_column')}
        - 过滤字段: {schema_analysis.get('filter_columns')}
        - 分组字段: {schema_analysis.get('groupby_columns')}
        
        时间上下文：
        - 开始时间: {time_context.report_start_date}
        - 结束时间: {time_context.report_end_date}
        - 时间粒度: {time_context.time_granularity}
        
        任务上下文：
        - 业务领域: {task_context.business_domain}
        - 报告类型: {task_context.report_type}
        
        要求：
        1. 生成完整的SQL查询语句
        2. 包含适当的时间过滤条件
        3. 添加必要的JOIN、GROUP BY、ORDER BY
        4. 确保语法正确且高效
        5. 添加适当的注释
        
        返回JSON格式：
        - sql_query: 完整SQL查询
        - explanation: 详细解释
        - confidence_score: 信心度 (0.0-1.0)
        - used_tables: 使用的表列表
        - used_columns: 使用的字段列表
        - time_filters: 时间过滤条件列表
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="sql_generation",
                complexity=model_selection.complexity.value
            )
            
            result_data = json.loads(response)
            
            return SqlGenerationResult(
                sql_query=result_data.get("sql_query", ""),
                explanation=result_data.get("explanation", ""),
                confidence_score=result_data.get("confidence_score", 0.7),
                used_tables=result_data.get("used_tables", []),
                used_columns=result_data.get("used_columns", []),
                time_filters=result_data.get("time_filters", [])
            )
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            return SqlGenerationResult(
                sql_query="",
                explanation=f"SQL生成失败: {str(e)}",
                confidence_score=0.0,
                used_tables=[],
                used_columns=[],
                time_filters=[],
                validation_errors=[str(e)]
            )
    
    async def _validate_and_correct_sql(
        self,
        sql_result: SqlGenerationResult,
        data_source_context: DataSourceContext,
        placeholder_context: PlaceholderContext
    ) -> SqlGenerationResult:
        """验证并纠错SQL"""
        
        if not sql_result.sql_query:
            return sql_result
            
        max_correction_attempts = 3
        current_sql = sql_result.sql_query
        correction_attempts = 0
        
        while correction_attempts < max_correction_attempts:
            # 语法验证
            syntax_errors = await self._validate_sql_syntax(current_sql, data_source_context)
            
            if not syntax_errors:
                logger.info("SQL语法验证通过")
                break
                
            # SQL纠错
            correction_attempts += 1
            logger.warning(f"SQL语法错误，进行第 {correction_attempts} 次纠错")
            
            corrected_sql = await self._correct_sql_errors(
                current_sql,
                syntax_errors,
                data_source_context,
                placeholder_context
            )
            
            if corrected_sql != current_sql:
                current_sql = corrected_sql
            else:
                logger.error("SQL纠错无效，停止尝试")
                break
        
        # 更新结果
        sql_result.sql_query = current_sql
        sql_result.correction_attempts = correction_attempts
        if correction_attempts > 0:
            sql_result.confidence_score *= (1.0 - 0.2 * correction_attempts)  # 每次纠错降低信心度
            
        return sql_result
    
    async def _validate_sql_syntax(
        self,
        sql_query: str,
        data_source_context: DataSourceContext
    ) -> List[str]:
        """验证SQL语法"""
        
        errors = []
        
        # 基础语法检查
        if not sql_query.strip():
            errors.append("SQL查询为空")
            return errors
            
        # 检查关键词
        sql_upper = sql_query.upper()
        if not sql_upper.strip().startswith(('SELECT', 'WITH')):
            errors.append("SQL必须以SELECT或WITH开头")
            
        # 检查表名是否存在
        used_tables = self._extract_table_names(sql_query)
        for table in used_tables:
            if table not in data_source_context.available_tables:
                errors.append(f"表 {table} 不存在于数据源中")
                
        # 检查基础语法错误
        if sql_query.count('(') != sql_query.count(')'):
            errors.append("括号不匹配")
            
        return errors
    
    def _extract_table_names(self, sql_query: str) -> List[str]:
        """从SQL中提取表名"""
        # 简化的表名提取逻辑
        import re
        pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql_query, re.IGNORECASE)
        return list(set(matches))
    
    async def _correct_sql_errors(
        self,
        sql_query: str,
        errors: List[str],
        data_source_context: DataSourceContext,
        placeholder_context: PlaceholderContext
    ) -> str:
        """纠正SQL错误"""
        
        step_context = StepContext(
            step=ProcessingStep.SQL_ERROR_CORRECTION,
            task_description=f"纠正占位符 {placeholder_context.placeholder_name} 的SQL错误",
            previous_errors=len(errors)
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请纠正以下SQL查询中的错误：
        
        原始SQL：
        ```sql
        {sql_query}
        ```
        
        发现的错误：
        {chr(10).join(f"- {error}" for error in errors)}
        
        数据源信息：
        - 可用表: {', '.join(data_source_context.available_tables)}
        - 数据源类型: {data_source_context.source_type}
        
        请返回纠正后的SQL查询，确保：
        1. 修复所有语法错误
        2. 使用正确的表名和字段名
        3. 保持原始查询的业务逻辑
        4. 符合 {data_source_context.source_type} 数据库的语法规范
        
        只返回纠正后的SQL查询，不要其他解释：
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="sql_correction",
                complexity=model_selection.complexity.value
            )
            
            # 提取SQL（移除可能的markdown格式）
            corrected_sql = response.strip()
            if corrected_sql.startswith('```sql'):
                corrected_sql = corrected_sql[6:]
            if corrected_sql.endswith('```'):
                corrected_sql = corrected_sql[:-3]
            corrected_sql = corrected_sql.strip()
            
            logger.info("SQL纠错完成")
            return corrected_sql
            
        except Exception as e:
            logger.error(f"SQL纠错失败: {e}")
            return sql_query  # 返回原始SQL
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        return {
            "model_selector_stats": self.model_selector.get_selection_statistics(),
            "correction_history": dict(self.correction_history)
        }


def create_placeholder_to_sql_agent(user_id: str) -> PlaceholderToSqlAgent:
    """创建占位符→SQL转换Agent实例"""
    if not user_id:
        raise ValueError("user_id is required for PlaceholderToSqlAgent")
    return PlaceholderToSqlAgent(user_id)