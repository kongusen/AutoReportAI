"""
增强的质量评分系统

提供多维度的质量评分机制，包括：
1. 语法评分 - SQL 语法正确性
2. 执行评分 - SQL 执行成功率
3. 数据质量评分 - 数据完整性和一致性
4. 工具使用评分 - 工具调用的合理性
5. 性能评分 - 查询性能和效率
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """质量评分维度"""
    SYNTAX = "syntax"               # 语法正确性
    EXECUTION = "execution"         # 执行成功率
    DATA_QUALITY = "data_quality"   # 数据质量
    TOOL_USAGE = "tool_usage"       # 工具使用
    PERFORMANCE = "performance"     # 性能


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: QualityDimension
    score: float  # 0.0 - 1.0
    weight: float  # 权重
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityScore:
    """质量评分结果"""
    overall_score: float  # 总体评分 0.0 - 1.0
    dimension_scores: Dict[QualityDimension, DimensionScore]
    grade: str  # A, B, C, D, F
    passed: bool  # 是否通过质量阈值
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """计算等级"""
        if self.overall_score >= 0.9:
            self.grade = "A"
        elif self.overall_score >= 0.8:
            self.grade = "B"
        elif self.overall_score >= 0.7:
            self.grade = "C"
        elif self.overall_score >= 0.6:
            self.grade = "D"
        else:
            self.grade = "F"


@dataclass
class QualityScorerConfig:
    """质量评分器配置"""
    # 权重配置
    weights: Dict[QualityDimension, float] = field(default_factory=lambda: {
        QualityDimension.SYNTAX: 0.25,
        QualityDimension.EXECUTION: 0.30,
        QualityDimension.DATA_QUALITY: 0.20,
        QualityDimension.TOOL_USAGE: 0.15,
        QualityDimension.PERFORMANCE: 0.10,
    })

    # 质量阈值
    passing_threshold: float = 0.7

    # 启用的维度
    enabled_dimensions: List[QualityDimension] = field(default_factory=lambda: [
        QualityDimension.SYNTAX,
        QualityDimension.EXECUTION,
        QualityDimension.DATA_QUALITY,
        QualityDimension.TOOL_USAGE,
        QualityDimension.PERFORMANCE,
    ])

    # SQL 验证配置
    sql_validation: Dict[str, Any] = field(default_factory=lambda: {
        "check_syntax": True,
        "check_structure": True,
        "check_keywords": True,
        "required_clauses": ["SELECT", "FROM"],
        "dangerous_keywords": ["DROP", "TRUNCATE", "DELETE"],
    })

    # 数据质量配置
    data_quality: Dict[str, Any] = field(default_factory=lambda: {
        "max_null_ratio": 0.5,  # 最大空值比例
        "min_row_count": 1,     # 最小行数
        "check_type_consistency": True,
        "check_value_range": True,
    })

    # 性能配置
    performance: Dict[str, Any] = field(default_factory=lambda: {
        "max_execution_time_ms": 5000,  # 最大执行时间 5秒
        "max_row_count": 10000,          # 最大行数
        "warn_execution_time_ms": 2000,  # 警告执行时间 2秒
    })


class EnhancedQualityScorer:
    """
    增强的质量评分器

    提供多维度的质量评分，包括语法、执行、数据质量、工具使用和性能评分
    """

    def __init__(self, config: Optional[QualityScorerConfig] = None):
        """
        Args:
            config: 质量评分器配置
        """
        self.config = config or QualityScorerConfig()
        self._validate_config()

        logger.info("🎯 [EnhancedQualityScorer] 初始化完成")
        logger.info(f"   启用的维度: {[d.value for d in self.config.enabled_dimensions]}")
        logger.info(f"   质量阈值: {self.config.passing_threshold}")

    def _validate_config(self):
        """验证配置"""
        # 确保权重总和为 1.0
        enabled_weights = {
            dim: weight
            for dim, weight in self.config.weights.items()
            if dim in self.config.enabled_dimensions
        }

        total_weight = sum(enabled_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            # 归一化权重
            normalized_weights = {
                dim: weight / total_weight
                for dim, weight in enabled_weights.items()
            }
            self.config.weights.update(normalized_weights)
            logger.warning(f"⚠️ 权重已归一化: {self.config.weights}")

    async def calculate_quality_score(
        self,
        content: str,
        execution_result: Optional[Dict[str, Any]] = None,
        tool_call_history: Optional[List[Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        data_source_service: Optional[Any] = None,
        connection_config: Optional[Dict[str, Any]] = None
    ) -> QualityScore:
        """
        计算质量评分

        Args:
            content: 生成的内容（通常是 SQL）
            execution_result: 执行结果
            tool_call_history: 工具调用历史
            request_context: 请求上下文
            data_source_service: 数据源服务（用于执行SQL验证）
            connection_config: 连接配置（用于执行SQL验证）

        Returns:
            QualityScore: 质量评分结果
        """
        logger.info("🎯 [EnhancedQualityScorer] 开始计算质量评分")

        # 如果没有执行结果但有数据源服务，尝试执行SQL验证
        if execution_result is None and data_source_service and connection_config and self._is_sql_content(content):
            logger.info("🔍 [质量评分] 尝试执行SQL验证")
            try:
                execution_result = await self._execute_sql_for_validation(content, data_source_service, connection_config)
                if execution_result:
                    logger.info(f"✅ [质量评分] SQL执行验证成功: {execution_result.get('success', False)}")
                else:
                    logger.warning("⚠️ [质量评分] SQL执行验证失败")
            except Exception as e:
                logger.warning(f"⚠️ [质量评分] SQL执行验证异常: {e}")
                execution_result = {"success": False, "error": str(e)}

        dimension_scores = {}

        # 1. 语法评分
        if QualityDimension.SYNTAX in self.config.enabled_dimensions:
            syntax_score = self._score_syntax(content)
            dimension_scores[QualityDimension.SYNTAX] = syntax_score
            logger.info(f"   语法评分: {syntax_score.score:.2f}")

        # 2. 执行评分
        if QualityDimension.EXECUTION in self.config.enabled_dimensions:
            execution_score = self._score_execution(execution_result)
            dimension_scores[QualityDimension.EXECUTION] = execution_score
            logger.info(f"   执行评分: {execution_score.score:.2f}")

        # 3. 数据质量评分
        if QualityDimension.DATA_QUALITY in self.config.enabled_dimensions:
            data_quality_score = self._score_data_quality(execution_result)
            dimension_scores[QualityDimension.DATA_QUALITY] = data_quality_score
            logger.info(f"   数据质量评分: {data_quality_score.score:.2f}")

        # 4. 工具使用评分
        if QualityDimension.TOOL_USAGE in self.config.enabled_dimensions:
            tool_usage_score = self._score_tool_usage(tool_call_history, request_context)
            dimension_scores[QualityDimension.TOOL_USAGE] = tool_usage_score
            logger.info(f"   工具使用评分: {tool_usage_score.score:.2f}")

        # 5. 性能评分
        if QualityDimension.PERFORMANCE in self.config.enabled_dimensions:
            performance_score = self._score_performance(execution_result)
            dimension_scores[QualityDimension.PERFORMANCE] = performance_score
            logger.info(f"   性能评分: {performance_score.score:.2f}")

        # 计算总体评分（加权平均）
        overall_score = self._calculate_overall_score(dimension_scores)

        # 严格规则：SQL 验证必须通过，否则直接判定为不通过并限制分数
        if self._is_sql_content(content):
            validation_success = None
            is_valid_flag = None
            if execution_result is not None and isinstance(execution_result, dict):
                validation_success = execution_result.get("success")
                # 兼容不同验证器字段
                is_valid_flag = execution_result.get("is_valid", execution_result.get("validated"))

            if validation_success is False or is_valid_flag is False:
                overall_score = min(overall_score, 0.49)
                logger.info("⚠️ [质量评分] SQL验证未通过，限制总体评分 ≤ 0.49")

        # 收集所有建议
        all_suggestions = []
        for dim_score in dimension_scores.values():
            all_suggestions.extend(dim_score.suggestions)

        # 创建质量评分结果
        quality_score = QualityScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            grade="",  # 将在 __post_init__ 中计算
            passed=overall_score >= self.config.passing_threshold,
            suggestions=all_suggestions,
            metadata={
                "weights": self.config.weights,
                "threshold": self.config.passing_threshold,
            }
        )

        logger.info(f"✅ [EnhancedQualityScorer] 质量评分完成")
        logger.info(f"   总体评分: {quality_score.overall_score:.2f}")
        logger.info(f"   等级: {quality_score.grade}")
        logger.info(f"   是否通过: {'✓' if quality_score.passed else '✗'}")

        return quality_score

    def _score_syntax(self, content: str) -> DimensionScore:
        """语法评分"""
        score = 0.0
        details = {}
        suggestions = []

        if not content or not content.strip():
            return DimensionScore(
                dimension=QualityDimension.SYNTAX,
                score=0.0,
                weight=self.config.weights.get(QualityDimension.SYNTAX, 0.0),
                details={"error": "内容为空"},
                suggestions=["生成的内容为空，请检查生成逻辑"]
            )

        content_upper = content.upper()

        # 1. 基础分（有内容）
        score += 0.2
        details["has_content"] = True

        # 2. 检查必需的 SQL 子句
        required_clauses = self.config.sql_validation.get("required_clauses", ["SELECT", "FROM"])
        found_clauses = []
        missing_clauses = []

        for clause in required_clauses:
            if clause in content_upper:
                found_clauses.append(clause)
                score += 0.15
            else:
                missing_clauses.append(clause)

        details["found_clauses"] = found_clauses
        details["missing_clauses"] = missing_clauses

        if missing_clauses:
            suggestions.append(f"缺少必需的 SQL 子句: {', '.join(missing_clauses)}")

        # 3. 检查 SQL 结构完整性
        structure_checks = {
            "has_from": "FROM" in content_upper,
            "has_where": "WHERE" in content_upper or "GROUP BY" in content_upper,
            "has_order": "ORDER BY" in content_upper,
            "has_limit": "LIMIT" in content_upper,
        }

        details["structure"] = structure_checks

        # FROM 子句最重要
        if structure_checks["has_from"]:
            score += 0.20
        else:
            suggestions.append("缺少 FROM 子句，查询不完整")

        # 其他结构加分
        if structure_checks["has_where"]:
            score += 0.15
        if structure_checks["has_order"]:
            score += 0.10

        # 4. 检查危险关键词
        dangerous_keywords = self.config.sql_validation.get("dangerous_keywords", [])
        found_dangerous = []

        for keyword in dangerous_keywords:
            if keyword in content_upper:
                found_dangerous.append(keyword)
                score -= 0.2  # 扣分

        if found_dangerous:
            details["dangerous_keywords"] = found_dangerous
            suggestions.append(f"⚠️ 包含危险关键词: {', '.join(found_dangerous)}")

        # 5. 检查语法问题
        syntax_issues = self._check_sql_syntax_issues(content)
        if syntax_issues:
            details["syntax_issues"] = syntax_issues
            suggestions.extend(syntax_issues)
            score -= len(syntax_issues) * 0.05

        # 确保分数在 0-1 之间
        score = max(0.0, min(1.0, score))

        return DimensionScore(
            dimension=QualityDimension.SYNTAX,
            score=score,
            weight=self.config.weights.get(QualityDimension.SYNTAX, 0.0),
            details=details,
            suggestions=suggestions
        )

    def _check_sql_syntax_issues(self, content: str) -> List[str]:
        """检查 SQL 语法问题"""
        issues = []

        # 检查是否有未配对的括号
        if content.count('(') != content.count(')'):
            issues.append("括号未配对")

        # 检查是否有未配对的引号
        single_quotes = content.count("'") - content.count("\\'")
        if single_quotes % 2 != 0:
            issues.append("单引号未配对")

        # 检查是否有连续的逗号
        if ',,' in content:
            issues.append("存在连续的逗号")

        # 检查是否有不完整的 SQL（以逗号或 AND/OR 结尾）
        stripped = content.strip()
        if stripped.endswith(',') or stripped.upper().endswith(' AND') or stripped.upper().endswith(' OR'):
            issues.append("SQL 语句不完整")

        return issues

    def _score_execution(self, execution_result: Optional[Dict[str, Any]]) -> DimensionScore:
        """执行评分"""
        score = 0.0
        details = {}
        suggestions = []

        if execution_result is None:
            # 没有执行结果，给予中性评分
            return DimensionScore(
                dimension=QualityDimension.EXECUTION,
                score=0.5,
                weight=self.config.weights.get(QualityDimension.EXECUTION, 0.0),
                details={"status": "not_executed"},
                suggestions=["未执行 SQL，无法评估执行质量"]
            )

        # 1. 检查执行是否成功
        success = execution_result.get("success", False)
        details["success"] = success

        if success:
            score += 0.6  # 执行成功是最重要的
            details["status"] = "success"
        else:
            error = execution_result.get("error", "Unknown error")
            details["status"] = "failed"
            details["error"] = error
            suggestions.append(f"SQL 执行失败: {error}")
            return DimensionScore(
                dimension=QualityDimension.EXECUTION,
                score=0.0,
                weight=self.config.weights.get(QualityDimension.EXECUTION, 0.0),
                details=details,
                suggestions=suggestions
            )

        # 2. 检查返回的数据
        rows = execution_result.get("rows") or execution_result.get("data", [])
        row_count = len(rows) if rows else execution_result.get("row_count", 0)
        details["row_count"] = row_count

        if row_count == 0:
            score += 0.2  # 执行成功但无数据
            suggestions.append("查询返回0行，请检查查询条件是否正确")
        elif row_count > 0:
            score += 0.4  # 有数据

            # 检查行数是否合理
            max_row_count = self.config.performance.get("max_row_count", 10000)
            if row_count > max_row_count:
                suggestions.append(f"返回行数过多 ({row_count} 行)，建议添加 LIMIT 子句")

        return DimensionScore(
            dimension=QualityDimension.EXECUTION,
            score=score,
            weight=self.config.weights.get(QualityDimension.EXECUTION, 0.0),
            details=details,
            suggestions=suggestions
        )

    def _score_data_quality(self, execution_result: Optional[Dict[str, Any]]) -> DimensionScore:
        """数据质量评分"""
        score = 0.0
        details = {}
        suggestions = []

        if execution_result is None or not execution_result.get("success", False):
            # 没有执行结果或执行失败，无法评估数据质量
            return DimensionScore(
                dimension=QualityDimension.DATA_QUALITY,
                score=0.5,
                weight=self.config.weights.get(QualityDimension.DATA_QUALITY, 0.0),
                details={"status": "not_available"},
                suggestions=[]
            )

        rows = execution_result.get("rows") or execution_result.get("data", [])

        if not rows or len(rows) == 0:
            # 无数据，给予中性评分
            return DimensionScore(
                dimension=QualityDimension.DATA_QUALITY,
                score=0.5,
                weight=self.config.weights.get(QualityDimension.DATA_QUALITY, 0.0),
                details={"status": "no_data"},
                suggestions=[]
            )

        # 1. 基础分（有数据）
        score += 0.3
        details["has_data"] = True

        # 2. 检查空值比例
        null_ratio = self._calculate_null_ratio(rows)
        details["null_ratio"] = null_ratio

        max_null_ratio = self.config.data_quality.get("max_null_ratio", 0.5)
        if null_ratio <= max_null_ratio:
            score += 0.3
        else:
            suggestions.append(f"数据空值比例过高 ({null_ratio:.1%})，建议检查数据质量")

        # 3. 检查数据类型一致性
        if self.config.data_quality.get("check_type_consistency", True):
            type_consistency = self._check_type_consistency(rows)
            details["type_consistency"] = type_consistency

            if type_consistency:
                score += 0.2
            else:
                suggestions.append("数据类型不一致，可能存在数据质量问题")

        # 4. 检查数据范围合理性
        if self.config.data_quality.get("check_value_range", True):
            range_check = self._check_value_range(rows)
            details["range_check"] = range_check

            if range_check.get("all_valid", True):
                score += 0.2
            else:
                invalid_fields = range_check.get("invalid_fields", [])
                if invalid_fields:
                    suggestions.append(f"以下字段有异常值: {', '.join(invalid_fields)}")

        return DimensionScore(
            dimension=QualityDimension.DATA_QUALITY,
            score=score,
            weight=self.config.weights.get(QualityDimension.DATA_QUALITY, 0.0),
            details=details,
            suggestions=suggestions
        )

    def _calculate_null_ratio(self, rows: List[Any]) -> float:
        """计算空值比例"""
        if not rows:
            return 0.0

        total_values = 0
        null_values = 0

        for row in rows:
            if isinstance(row, dict):
                values = list(row.values())
            elif isinstance(row, (list, tuple)):
                values = list(row)
            else:
                continue

            for value in values:
                total_values += 1
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    null_values += 1

        if total_values == 0:
            return 0.0

        return null_values / total_values

    def _check_type_consistency(self, rows: List[Any]) -> bool:
        """检查数据类型一致性"""
        if not rows or len(rows) < 2:
            return True  # 少于2行，无法检查

        # 获取第一行的类型作为参考
        first_row = rows[0]

        if isinstance(first_row, dict):
            reference_types = {key: type(value) for key, value in first_row.items()}

            # 检查其他行是否类型一致
            for row in rows[1:]:
                if not isinstance(row, dict):
                    return False

                for key, value in row.items():
                    if key in reference_types:
                        if value is not None and not isinstance(value, reference_types[key]):
                            # 允许数字类型之间的转换
                            if not (isinstance(value, (int, float)) and isinstance(reference_types[key], (int, float))):
                                return False

        return True

    def _check_value_range(self, rows: List[Any]) -> Dict[str, Any]:
        """检查数值范围合理性"""
        result = {"all_valid": True, "invalid_fields": []}

        if not rows:
            return result

        first_row = rows[0]
        if not isinstance(first_row, dict):
            return result

        # 检查数值字段
        for key in first_row.keys():
            values = []
            for row in rows:
                if isinstance(row, dict) and key in row:
                    value = row[key]
                    if isinstance(value, (int, float)) and value is not None:
                        values.append(value)

            if not values:
                continue

            # 检查是否有异常值（简单的异常值检测）
            mean = sum(values) / len(values)
            std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5

            # 3-sigma 规则
            outliers = [v for v in values if abs(v - mean) > 3 * std]
            if outliers:
                result["all_valid"] = False
                result["invalid_fields"].append(key)

        return result

    def _score_tool_usage(
        self,
        tool_call_history: Optional[List[Any]],
        request_context: Optional[Dict[str, Any]]
    ) -> DimensionScore:
        """工具使用评分"""
        score = 0.0
        details = {}
        suggestions = []

        if not tool_call_history:
            # 没有工具调用历史
            return DimensionScore(
                dimension=QualityDimension.TOOL_USAGE,
                score=0.3,  # 给予低分，因为可能没有充分利用工具
                weight=self.config.weights.get(QualityDimension.TOOL_USAGE, 0.0),
                details={"tool_calls": 0},
                suggestions=["❌ 未使用任何工具！请立即调用 schema_discovery 或 schema_retrieval 工具获取表结构信息"]
            )

        tool_call_count = len(tool_call_history)
        details["tool_call_count"] = tool_call_count

        # 1. 工具调用次数评分
        if tool_call_count >= 1:
            score += 0.3
        if tool_call_count >= 3:
            score += 0.2
        if tool_call_count >= 5:
            score += 0.1

        # 2. 工具调用成功率
        successful_calls = sum(1 for call in tool_call_history if getattr(call, 'success', True))
        success_rate = successful_calls / tool_call_count if tool_call_count > 0 else 0.0
        details["success_rate"] = success_rate

        if success_rate >= 0.9:
            score += 0.2
        elif success_rate >= 0.7:
            score += 0.1
        else:
            suggestions.append(f"工具调用成功率较低 ({success_rate:.1%})，请检查工具使用方式")

        # 3. 工具类型多样性
        tool_names = [getattr(call, 'tool_name', 'unknown') for call in tool_call_history]
        unique_tools = len(set(tool_names))
        details["unique_tools"] = unique_tools

        if unique_tools >= 3:
            score += 0.2
        elif unique_tools >= 2:
            score += 0.1

        # 4. 检查是否使用了关键工具（如 schema_retrieval, sql_validator）
        key_tools = ["schema_retrieval", "schema_discovery", "sql_validator", "sql_column_checker"]
        used_key_tools = [tool for tool in tool_names if tool in key_tools]
        details["used_key_tools"] = used_key_tools

        if len(used_key_tools) >= 2:
            score += 0.1
        elif len(used_key_tools) == 0:
            suggestions.append("❌ 未使用关键工具！请使用 schema_retrieval 获取表结构，然后生成SQL")
        elif "schema_discovery" in tool_names and "schema_retrieval" not in tool_names:
            suggestions.append("✅ 已使用 schema_discovery，现在请使用 schema_retrieval 获取 ods_refund 表的详细结构")
        elif "schema_retrieval" in tool_names and "sql_generator" not in tool_names:
            suggestions.append("✅ 已获取表结构，现在请生成SQL查询")

        # 🔥 新增：检查是否陷入循环
        if tool_call_count > 3:
            # 检查是否有重复的工具调用
            tool_counts = {}
            for tool_name in tool_names:
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
            repeated_tools = [tool for tool, count in tool_counts.items() if count > 1]
            if repeated_tools:
                suggestions.append(f"⚠️ 检测到重复调用工具: {repeated_tools}，请停止循环，直接生成SQL")
                score -= 0.2  # 扣分

        return DimensionScore(
            dimension=QualityDimension.TOOL_USAGE,
            score=score,
            weight=self.config.weights.get(QualityDimension.TOOL_USAGE, 0.0),
            details=details,
            suggestions=suggestions
        )

    def _score_performance(self, execution_result: Optional[Dict[str, Any]]) -> DimensionScore:
        """性能评分"""
        score = 0.0
        details = {}
        suggestions = []

        if execution_result is None or not execution_result.get("success", False):
            # 没有执行结果或执行失败，给予中性评分
            return DimensionScore(
                dimension=QualityDimension.PERFORMANCE,
                score=0.5,
                weight=self.config.weights.get(QualityDimension.PERFORMANCE, 0.0),
                details={"status": "not_available"},
                suggestions=[]
            )

        # 1. 执行时间评分
        execution_time_ms = execution_result.get("execution_time_ms") or execution_result.get("execution_time", 0)
        details["execution_time_ms"] = execution_time_ms

        max_time = self.config.performance.get("max_execution_time_ms", 5000)
        warn_time = self.config.performance.get("warn_execution_time_ms", 2000)

        if execution_time_ms <= warn_time:
            score += 0.5  # 优秀
        elif execution_time_ms <= max_time:
            score += 0.3  # 良好
            suggestions.append(f"查询执行时间较长 ({execution_time_ms}ms)，建议优化")
        else:
            score += 0.1  # 较慢
            suggestions.append(f"查询执行时间过长 ({execution_time_ms}ms)，请优化查询或添加索引")

        # 2. 数据量评分
        row_count = execution_result.get("row_count", 0)
        if row_count == 0:
            rows = execution_result.get("rows") or execution_result.get("data", [])
            row_count = len(rows) if rows else 0

        details["row_count"] = row_count

        max_rows = self.config.performance.get("max_row_count", 10000)

        if row_count <= 1000:
            score += 0.3  # 数据量合理
        elif row_count <= max_rows:
            score += 0.2
            suggestions.append(f"返回数据量较大 ({row_count} 行)，建议添加 LIMIT 或分页")
        else:
            score += 0.1
            suggestions.append(f"返回数据量过大 ({row_count} 行)，强烈建议添加 LIMIT 或分页")

        # 3. 查询复杂度（基于执行计划，如果有）
        if "explain" in execution_result or "query_plan" in execution_result:
            # 这里可以添加更复杂的查询计划分析
            score += 0.2

        return DimensionScore(
            dimension=QualityDimension.PERFORMANCE,
            score=score,
            weight=self.config.weights.get(QualityDimension.PERFORMANCE, 0.0),
            details=details,
            suggestions=suggestions
        )

    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, DimensionScore]) -> float:
        """计算总体评分（加权平均）"""
        if not dimension_scores:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for dimension, dim_score in dimension_scores.items():
            weighted_sum += dim_score.score * dim_score.weight
            total_weight += dim_score.weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _is_sql_content(self, content: str) -> bool:
        """检查内容是否是SQL查询"""
        if not content or not content.strip():
            return False
        
        content_upper = content.strip().upper()
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "SHOW", "DESCRIBE", "EXPLAIN"]
        
        # 检查是否以SQL关键字开头
        return any(content_upper.startswith(keyword) for keyword in sql_keywords)
    
    async def _execute_sql_for_validation(self, sql: str, data_source_service: Any, connection_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行SQL进行验证"""
        try:
            # 添加LIMIT限制，避免返回过多数据
            test_sql = sql.strip()
            if "LIMIT" not in test_sql.upper():
                test_sql += " LIMIT 10"
            
            logger.debug(f"🔍 [质量评分] 执行验证SQL: {test_sql[:100]}...")
            
            # 执行查询
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=test_sql,
                limit=10
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [质量评分] SQL执行验证失败: {e}")
            return {"success": False, "error": str(e)}


# 工厂函数
def create_quality_scorer(config: Optional[QualityScorerConfig] = None) -> EnhancedQualityScorer:
    """创建质量评分器"""
    return EnhancedQualityScorer(config)


def create_strict_quality_scorer() -> EnhancedQualityScorer:
    """创建严格的质量评分器"""
    config = QualityScorerConfig(
        passing_threshold=0.85,  # 提高阈值
        weights={
            QualityDimension.SYNTAX: 0.20,
            QualityDimension.EXECUTION: 0.40,  # 更重视执行
            QualityDimension.DATA_QUALITY: 0.25,  # 更重视数据质量
            QualityDimension.TOOL_USAGE: 0.10,
            QualityDimension.PERFORMANCE: 0.05,
        }
    )
    return EnhancedQualityScorer(config)


def create_lenient_quality_scorer() -> EnhancedQualityScorer:
    """创建宽松的质量评分器"""
    config = QualityScorerConfig(
        passing_threshold=0.6,  # 降低阈值
        weights={
            QualityDimension.SYNTAX: 0.30,
            QualityDimension.EXECUTION: 0.25,
            QualityDimension.DATA_QUALITY: 0.15,
            QualityDimension.TOOL_USAGE: 0.20,
            QualityDimension.PERFORMANCE: 0.10,
        }
    )
    return EnhancedQualityScorer(config)


# 导出
__all__ = [
    "QualityDimension",
    "DimensionScore",
    "QualityScore",
    "QualityScorerConfig",
    "EnhancedQualityScorer",
    "create_quality_scorer",
    "create_strict_quality_scorer",
    "create_lenient_quality_scorer",
]
