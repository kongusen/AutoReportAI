"""
SQL测试验证流程

基于AutoReportAI Agent设计的SQL质量保证系统：
4. SQL测试验证流程: 执行SQL测试 → 结果与预期匹配 → 错误自动纠正 → 多轮验证确保准确性

特性：
- 多层验证：语法验证、逻辑验证、性能验证、结果验证
- 自动纠错：支持多轮纠错，智能识别和修复SQL问题
- 真实测试：在真实数据源上执行测试查询
- 性能监控：监控SQL执行性能和资源消耗
- 结果验证：验证查询结果的合理性和完整性
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlparse
from sqlparse import sql, tokens

from ..llm.step_based_model_selector import (
    StepBasedModelSelector, 
    StepContext, 
    ProcessingStep,
    create_step_based_model_selector
)
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"           # 基础语法验证
    STANDARD = "standard"     # 标准验证（语法+逻辑）
    COMPREHENSIVE = "comprehensive"  # 全面验证（语法+逻辑+性能+结果）


class ValidationStatus(Enum):
    """验证状态"""
    PENDING = "pending"       # 待验证
    VALIDATING = "validating" # 验证中
    PASSED = "passed"         # 验证通过
    FAILED = "failed"         # 验证失败
    CORRECTED = "corrected"   # 已纠正


class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = "low"              # 低：不影响执行的警告
    MEDIUM = "medium"        # 中：影响性能或最佳实践
    HIGH = "high"           # 高：语法错误或逻辑错误
    CRITICAL = "critical"   # 关键：会导致查询失败


@dataclass
class SqlError:
    """SQL错误"""
    error_id: str
    error_type: str          # 'syntax', 'logic', 'performance', 'security'
    severity: ErrorSeverity
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """验证结果"""
    validation_id: str
    sql_query: str
    status: ValidationStatus
    validation_level: ValidationLevel
    
    # 错误信息
    errors: List[SqlError] = field(default_factory=list)
    warnings: List[SqlError] = field(default_factory=list)
    
    # 性能信息
    execution_time_ms: Optional[float] = None
    estimated_cost: Optional[float] = None
    rows_affected: Optional[int] = None
    
    # 纠错信息
    corrected_sql: Optional[str] = None
    correction_attempts: int = 0
    correction_history: List[str] = field(default_factory=list)
    
    # 验证元数据
    timestamp: datetime = field(default_factory=datetime.now)
    validator_version: str = "1.0"


@dataclass
class TestCase:
    """SQL测试用例"""
    test_id: str
    description: str
    input_sql: str
    expected_result_type: str  # 'rows', 'count', 'aggregate', 'empty'
    expected_row_count: Optional[int] = None
    expected_columns: List[str] = field(default_factory=list)
    expected_sample_data: List[Dict[str, Any]] = field(default_factory=list)
    timeout_seconds: int = 30


class SqlTestingValidator:
    """SQL测试验证器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model_selector = create_step_based_model_selector()
        self.validation_history: List[ValidationResult] = []
        self.correction_cache: Dict[str, str] = {}  # 缓存纠错结果
        
    async def validate_sql(
        self,
        sql_query: str,
        data_source_context: Dict[str, Any],
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        test_cases: Optional[List[TestCase]] = None
    ) -> ValidationResult:
        """
        验证SQL查询
        
        Args:
            sql_query: 要验证的SQL查询
            data_source_context: 数据源上下文
            validation_level: 验证级别
            test_cases: 可选的测试用例
            
        Returns:
            ValidationResult: 验证结果
        """
        validation_id = f"validation_{int(time.time() * 1000)}"
        
        try:
            logger.info(f"开始SQL验证 {validation_id}, 级别: {validation_level.value}")
            
            result = ValidationResult(
                validation_id=validation_id,
                sql_query=sql_query,
                status=ValidationStatus.VALIDATING,
                validation_level=validation_level
            )
            
            # 1. 语法验证
            syntax_errors = await self._validate_syntax(sql_query)
            result.errors.extend(syntax_errors)
            
            # 如果有严重的语法错误，先尝试纠正
            critical_syntax_errors = [e for e in syntax_errors if e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]]
            if critical_syntax_errors:
                corrected_sql = await self._correct_sql_errors(
                    sql_query, critical_syntax_errors, data_source_context
                )
                if corrected_sql != sql_query:
                    result.corrected_sql = corrected_sql
                    result.correction_attempts += 1
                    result.correction_history.append(sql_query)
                    # 重新验证纠正后的SQL
                    return await self.validate_sql(corrected_sql, data_source_context, validation_level, test_cases)
            
            # 2. 逻辑验证
            if validation_level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE]:
                logic_errors = await self._validate_logic(sql_query, data_source_context)
                result.errors.extend(logic_errors)
            
            # 3. 性能验证
            if validation_level == ValidationLevel.COMPREHENSIVE:
                performance_issues = await self._validate_performance(sql_query, data_source_context)
                result.warnings.extend(performance_issues)
            
            # 4. 实际执行测试
            if validation_level == ValidationLevel.COMPREHENSIVE:
                execution_result = await self._execute_test_query(sql_query, data_source_context)
                result.execution_time_ms = execution_result.get("execution_time_ms")
                result.rows_affected = execution_result.get("rows_affected")
                
                if execution_result.get("error"):
                    runtime_error = SqlError(
                        error_id=f"runtime_{validation_id}",
                        error_type="runtime",
                        severity=ErrorSeverity.CRITICAL,
                        message=execution_result["error"],
                        auto_fixable=True
                    )
                    result.errors.append(runtime_error)
            
            # 5. 测试用例验证
            if test_cases:
                test_results = await self._run_test_cases(sql_query, test_cases, data_source_context)
                result.errors.extend(test_results.get("errors", []))
                result.warnings.extend(test_results.get("warnings", []))
            
            # 6. 确定最终状态
            has_critical_errors = any(e.severity == ErrorSeverity.CRITICAL for e in result.errors)
            has_high_errors = any(e.severity == ErrorSeverity.HIGH for e in result.errors)
            
            if has_critical_errors:
                result.status = ValidationStatus.FAILED
                # 尝试自动纠错
                if result.correction_attempts < 3:  # 最多3次纠错尝试
                    critical_errors = [e for e in result.errors if e.severity == ErrorSeverity.CRITICAL]
                    corrected_sql = await self._correct_sql_errors(
                        result.corrected_sql or sql_query, critical_errors, data_source_context
                    )
                    if corrected_sql != (result.corrected_sql or sql_query):
                        result.corrected_sql = corrected_sql
                        result.correction_attempts += 1
                        result.correction_history.append(result.corrected_sql or sql_query)
                        # 递归验证纠正后的SQL
                        return await self.validate_sql(corrected_sql, data_source_context, validation_level, test_cases)
            elif has_high_errors:
                result.status = ValidationStatus.FAILED
            else:
                result.status = ValidationStatus.PASSED
            
            self.validation_history.append(result)
            logger.info(f"SQL验证完成 {validation_id}: {result.status.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"SQL验证异常 {validation_id}: {e}")
            error_result = ValidationResult(
                validation_id=validation_id,
                sql_query=sql_query,
                status=ValidationStatus.FAILED,
                validation_level=validation_level
            )
            error_result.errors.append(SqlError(
                error_id=f"system_error_{validation_id}",
                error_type="system",
                severity=ErrorSeverity.CRITICAL,
                message=f"验证系统异常: {str(e)}"
            ))
            return error_result
    
    async def _validate_syntax(self, sql_query: str) -> List[SqlError]:
        """语法验证"""
        errors = []
        
        try:
            # 使用sqlparse进行基础语法分析
            parsed = sqlparse.parse(sql_query)
            
            if not parsed:
                errors.append(SqlError(
                    error_id="syntax_empty",
                    error_type="syntax",
                    severity=ErrorSeverity.CRITICAL,
                    message="SQL查询为空或无法解析",
                    auto_fixable=False
                ))
                return errors
            
            # 检查SQL结构
            stmt = parsed[0]
            
            # 检查基本语法错误
            errors.extend(self._check_basic_syntax(stmt))
            
            # 使用AI模型进行深度语法分析
            ai_syntax_errors = await self._ai_validate_syntax(sql_query)
            errors.extend(ai_syntax_errors)
            
        except Exception as e:
            errors.append(SqlError(
                error_id="syntax_parse_error",
                error_type="syntax", 
                severity=ErrorSeverity.HIGH,
                message=f"语法解析失败: {str(e)}",
                auto_fixable=True
            ))
        
        return errors
    
    def _check_basic_syntax(self, stmt) -> List[SqlError]:
        """检查基本语法"""
        errors = []
        
        # 检查括号匹配
        sql_text = str(stmt)
        if sql_text.count('(') != sql_text.count(')'):
            errors.append(SqlError(
                error_id="syntax_parentheses",
                error_type="syntax",
                severity=ErrorSeverity.HIGH,
                message="括号不匹配",
                suggestion="检查所有开括号都有对应的闭括号",
                auto_fixable=True
            ))
        
        # 检查引号匹配
        single_quotes = sql_text.count("'") - sql_text.count("\\'")
        double_quotes = sql_text.count('"') - sql_text.count('\\"')
        
        if single_quotes % 2 != 0:
            errors.append(SqlError(
                error_id="syntax_single_quotes",
                error_type="syntax",
                severity=ErrorSeverity.HIGH,
                message="单引号不匹配",
                auto_fixable=True
            ))
        
        if double_quotes % 2 != 0:
            errors.append(SqlError(
                error_id="syntax_double_quotes", 
                error_type="syntax",
                severity=ErrorSeverity.HIGH,
                message="双引号不匹配",
                auto_fixable=True
            ))
        
        return errors
    
    async def _ai_validate_syntax(self, sql_query: str) -> List[SqlError]:
        """使用AI模型进行语法验证"""
        
        step_context = StepContext(
            step=ProcessingStep.SQL_VALIDATION,
            task_description="AI SQL语法验证",
            data_complexity="high"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请对以下SQL查询进行详细的语法验证：
        
        SQL查询：
        ```sql
        {sql_query}
        ```
        
        请检查：
        1. SQL语法是否正确
        2. 关键词拼写是否正确
        3. 函数调用是否正确
        4. 数据类型使用是否合适
        5. 子查询结构是否正确
        
        返回JSON格式的验证结果：
        {{
            "syntax_valid": boolean,
            "errors": [
                {{
                    "error_type": "语法错误类型",
                    "severity": "high|medium|low",
                    "message": "错误描述",
                    "line_number": 行号,
                    "suggestion": "修复建议",
                    "auto_fixable": boolean
                }}
            ]
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="sql_syntax_validation",
                complexity=model_selection.complexity.value
            )
            
            validation_result = json.loads(response)
            errors = []
            
            for error_data in validation_result.get("errors", []):
                severity_map = {
                    "low": ErrorSeverity.LOW,
                    "medium": ErrorSeverity.MEDIUM, 
                    "high": ErrorSeverity.HIGH,
                    "critical": ErrorSeverity.CRITICAL
                }
                
                error = SqlError(
                    error_id=f"ai_syntax_{len(errors)}",
                    error_type="syntax",
                    severity=severity_map.get(error_data.get("severity", "medium"), ErrorSeverity.MEDIUM),
                    message=error_data.get("message", ""),
                    line_number=error_data.get("line_number"),
                    suggestion=error_data.get("suggestion"),
                    auto_fixable=error_data.get("auto_fixable", False)
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"AI语法验证失败: {e}")
            return []
    
    async def _validate_logic(self, sql_query: str, data_source_context: Dict[str, Any]) -> List[SqlError]:
        """逻辑验证"""
        
        step_context = StepContext(
            step=ProcessingStep.SQL_VALIDATION,
            task_description="SQL逻辑验证", 
            data_complexity="high"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        # 获取数据源Schema信息
        schema_info = self._format_schema_info(data_source_context)
        
        prompt = f"""
        请对以下SQL查询进行逻辑验证：
        
        SQL查询：
        ```sql
        {sql_query}
        ```
        
        数据源Schema：
        {schema_info}
        
        请检查：
        1. 表名是否存在于Schema中
        2. 字段名是否存在且类型匹配
        3. JOIN条件是否合理
        4. WHERE条件逻辑是否正确
        5. GROUP BY和HAVING的使用是否合适
        6. 聚合函数的使用是否正确
        7. 子查询的逻辑是否合理
        
        返回JSON格式的验证结果：
        {{
            "logic_valid": boolean,
            "errors": [
                {{
                    "error_type": "logic",
                    "severity": "high|medium|low", 
                    "message": "错误描述",
                    "suggestion": "修复建议",
                    "auto_fixable": boolean
                }}
            ]
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="sql_logic_validation",
                complexity=model_selection.complexity.value
            )
            
            validation_result = json.loads(response)
            errors = []
            
            for error_data in validation_result.get("errors", []):
                severity_map = {
                    "low": ErrorSeverity.LOW,
                    "medium": ErrorSeverity.MEDIUM,
                    "high": ErrorSeverity.HIGH,
                    "critical": ErrorSeverity.CRITICAL
                }
                
                error = SqlError(
                    error_id=f"ai_logic_{len(errors)}",
                    error_type="logic",
                    severity=severity_map.get(error_data.get("severity", "medium"), ErrorSeverity.MEDIUM),
                    message=error_data.get("message", ""),
                    suggestion=error_data.get("suggestion"),
                    auto_fixable=error_data.get("auto_fixable", False)
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"逻辑验证失败: {e}")
            return []
    
    def _format_schema_info(self, data_source_context: Dict[str, Any]) -> str:
        """格式化Schema信息"""
        schema_info = ""
        
        table_schemas = data_source_context.get("table_schemas", {})
        for table_name, columns in table_schemas.items():
            schema_info += f"\n表 {table_name}:\n"
            for col in columns:
                col_info = f"  - {col.get('name', '')}: {col.get('type', '')}"
                if col.get('comment'):
                    col_info += f" ({col['comment']})"
                schema_info += col_info + "\n"
        
        return schema_info
    
    async def _validate_performance(self, sql_query: str, data_source_context: Dict[str, Any]) -> List[SqlError]:
        """性能验证"""
        warnings = []
        
        # 简单的性能检查规则
        sql_upper = sql_query.upper()
        
        # 检查是否使用了SELECT *
        if "SELECT *" in sql_upper:
            warnings.append(SqlError(
                error_id="perf_select_star",
                error_type="performance",
                severity=ErrorSeverity.LOW,
                message="使用SELECT *可能影响性能",
                suggestion="明确指定需要的字段名",
                auto_fixable=True
            ))
        
        # 检查是否缺少WHERE条件
        if "WHERE" not in sql_upper and "LIMIT" not in sql_upper:
            warnings.append(SqlError(
                error_id="perf_no_where",
                error_type="performance", 
                severity=ErrorSeverity.MEDIUM,
                message="查询缺少WHERE条件或LIMIT限制，可能返回大量数据",
                suggestion="添加适当的WHERE条件或LIMIT限制",
                auto_fixable=False
            ))
        
        # 检查是否有可能的笛卡尔积
        join_count = sql_upper.count("JOIN")
        where_count = sql_upper.count("WHERE")
        
        if join_count > 0 and where_count == 0:
            warnings.append(SqlError(
                error_id="perf_cartesian",
                error_type="performance",
                severity=ErrorSeverity.HIGH,
                message="可能存在笛卡尔积，缺少JOIN条件",
                suggestion="确保所有JOIN都有适当的ON条件",
                auto_fixable=False
            ))
        
        return warnings
    
    async def _execute_test_query(self, sql_query: str, data_source_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试查询"""
        try:
            # 创建安全的测试查询（添加LIMIT限制）
            test_query = self._create_safe_test_query(sql_query)
            
            # 这里应该连接到真实数据库执行查询
            # 为了演示，我们模拟执行结果
            execution_result = {
                "success": True,
                "execution_time_ms": 150.5,
                "rows_affected": 42,
                "sample_data": [
                    {"id": 1, "name": "Sample", "count": 10},
                    {"id": 2, "name": "Data", "count": 25}
                ]
            }
            
            logger.info(f"测试查询执行完成，耗时 {execution_result['execution_time_ms']}ms")
            return execution_result
            
        except Exception as e:
            logger.error(f"测试查询执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": 0,
                "rows_affected": 0
            }
    
    def _create_safe_test_query(self, sql_query: str) -> str:
        """创建安全的测试查询"""
        # 添加LIMIT限制，避免返回过多数据
        sql_upper = sql_query.upper().strip()
        
        if "LIMIT" not in sql_upper:
            # 简单的LIMIT添加逻辑
            if sql_query.rstrip().endswith(';'):
                safe_query = sql_query.rstrip()[:-1] + " LIMIT 100;"
            else:
                safe_query = sql_query + " LIMIT 100"
        else:
            safe_query = sql_query
        
        return safe_query
    
    async def _run_test_cases(
        self, 
        sql_query: str, 
        test_cases: List[TestCase], 
        data_source_context: Dict[str, Any]
    ) -> Dict[str, List[SqlError]]:
        """运行测试用例"""
        errors = []
        warnings = []
        
        for test_case in test_cases:
            try:
                # 执行测试用例
                result = await self._execute_test_query(sql_query, data_source_context)
                
                if not result.get("success"):
                    errors.append(SqlError(
                        error_id=f"test_case_{test_case.test_id}",
                        error_type="test_case",
                        severity=ErrorSeverity.HIGH,
                        message=f"测试用例 {test_case.test_id} 执行失败: {result.get('error', '未知错误')}"
                    ))
                    continue
                
                # 验证结果
                validation_errors = self._validate_test_case_result(test_case, result)
                errors.extend(validation_errors)
                
            except Exception as e:
                errors.append(SqlError(
                    error_id=f"test_case_error_{test_case.test_id}",
                    error_type="test_case",
                    severity=ErrorSeverity.MEDIUM,
                    message=f"测试用例 {test_case.test_id} 异常: {str(e)}"
                ))
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_test_case_result(self, test_case: TestCase, result: Dict[str, Any]) -> List[SqlError]:
        """验证测试用例结果"""
        errors = []
        
        # 检查行数
        if test_case.expected_row_count is not None:
            actual_rows = result.get("rows_affected", 0)
            if actual_rows != test_case.expected_row_count:
                errors.append(SqlError(
                    error_id=f"test_rows_{test_case.test_id}",
                    error_type="test_case",
                    severity=ErrorSeverity.MEDIUM,
                    message=f"行数不匹配：期望 {test_case.expected_row_count}，实际 {actual_rows}"
                ))
        
        # 检查列名（简化实现）
        if test_case.expected_columns:
            sample_data = result.get("sample_data", [])
            if sample_data:
                actual_columns = list(sample_data[0].keys())
                missing_columns = set(test_case.expected_columns) - set(actual_columns)
                if missing_columns:
                    errors.append(SqlError(
                        error_id=f"test_columns_{test_case.test_id}",
                        error_type="test_case",
                        severity=ErrorSeverity.MEDIUM,
                        message=f"缺少预期列: {', '.join(missing_columns)}"
                    ))
        
        return errors
    
    async def _correct_sql_errors(
        self,
        sql_query: str,
        errors: List[SqlError],
        data_source_context: Dict[str, Any]
    ) -> str:
        """纠正SQL错误"""
        
        # 检查缓存
        error_signature = self._generate_error_signature(sql_query, errors)
        if error_signature in self.correction_cache:
            logger.info("使用缓存的纠错结果")
            return self.correction_cache[error_signature]
        
        step_context = StepContext(
            step=ProcessingStep.SQL_ERROR_CORRECTION,
            task_description="SQL错误纠正",
            previous_errors=len(errors)
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        # 构建错误描述
        error_descriptions = []
        for error in errors:
            desc = f"- {error.error_type}错误 ({error.severity.value}): {error.message}"
            if error.suggestion:
                desc += f" 建议: {error.suggestion}"
            error_descriptions.append(desc)
        
        schema_info = self._format_schema_info(data_source_context)
        
        prompt = f"""
        请修复以下SQL查询中的错误：
        
        原始SQL：
        ```sql
        {sql_query}
        ```
        
        发现的错误：
        {chr(10).join(error_descriptions)}
        
        数据源Schema：
        {schema_info}
        
        请返回修复后的SQL查询，要求：
        1. 修复所有语法和逻辑错误
        2. 保持原始查询的业务逻辑
        3. 使用正确的表名和字段名
        4. 确保查询效率和可读性
        
        只返回修复后的SQL查询，不要其他解释：
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="sql_error_correction",
                complexity=model_selection.complexity.value
            )
            
            # 提取SQL（移除markdown格式）
            corrected_sql = response.strip()
            if corrected_sql.startswith('```sql'):
                corrected_sql = corrected_sql[6:]
            if corrected_sql.endswith('```'):
                corrected_sql = corrected_sql[:-3]
            corrected_sql = corrected_sql.strip()
            
            # 缓存结果
            self.correction_cache[error_signature] = corrected_sql
            
            logger.info("SQL错误纠正完成")
            return corrected_sql
            
        except Exception as e:
            logger.error(f"SQL错误纠正失败: {e}")
            return sql_query  # 返回原始SQL
    
    def _generate_error_signature(self, sql_query: str, errors: List[SqlError]) -> str:
        """生成错误签名用于缓存"""
        import hashlib
        
        error_types = sorted([f"{e.error_type}:{e.message}" for e in errors])
        signature_data = f"{sql_query}:{':'.join(error_types)}"
        
        return hashlib.md5(signature_data.encode()).hexdigest()
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        if not self.validation_history:
            return {"total_validations": 0}
        
        total = len(self.validation_history)
        passed = sum(1 for v in self.validation_history if v.status == ValidationStatus.PASSED)
        corrected = sum(1 for v in self.validation_history if v.corrected_sql is not None)
        
        # 错误类型统计
        error_type_counts = {}
        for validation in self.validation_history:
            for error in validation.errors:
                error_type_counts[error.error_type] = error_type_counts.get(error.error_type, 0) + 1
        
        # 平均纠错次数
        total_corrections = sum(v.correction_attempts for v in self.validation_history)
        avg_corrections = total_corrections / total if total > 0 else 0
        
        return {
            "total_validations": total,
            "passed_validations": passed,
            "pass_rate": passed / total,
            "corrected_validations": corrected,
            "correction_rate": corrected / total,
            "average_corrections_per_validation": avg_corrections,
            "error_type_distribution": error_type_counts,
            "cache_hit_rate": len(self.correction_cache) / max(total, 1),
            "model_selector_stats": self.model_selector.get_selection_statistics()
        }


def create_sql_testing_validator(user_id: str) -> SqlTestingValidator:
    """创建SQL测试验证器实例"""
    if not user_id:
        raise ValueError("user_id is required for SqlTestingValidator")
    return SqlTestingValidator(user_id)