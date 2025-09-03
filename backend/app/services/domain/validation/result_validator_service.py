"""
结果验证器服务

负责验证数据结果的正确性、完整性和质量
"""

import logging
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"          # 基础验证
    STANDARD = "standard"    # 标准验证  
    STRICT = "strict"        # 严格验证
    COMPREHENSIVE = "comprehensive"  # 全面验证


class ValidationCriterion(Enum):
    """验证标准"""
    NOT_NULL = "not_null"
    DATA_TYPE = "data_type"
    RANGE = "range"
    FORMAT = "format"
    UNIQUENESS = "uniqueness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    BUSINESS_RULE = "business_rule"


@dataclass
class ValidationIssue:
    """验证问题"""
    criterion: ValidationCriterion
    severity: str  # error, warning, info
    message: str
    field_path: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    confidence: float
    quality_score: float
    issues: List[ValidationIssue]
    validated_result: Any
    metadata: Dict[str, Any]


class ResultValidatorService:
    """结果验证器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 默认验证标准
        self.default_criteria = {
            ValidationLevel.BASIC: [
                ValidationCriterion.NOT_NULL,
                ValidationCriterion.DATA_TYPE
            ],
            ValidationLevel.STANDARD: [
                ValidationCriterion.NOT_NULL,
                ValidationCriterion.DATA_TYPE,
                ValidationCriterion.FORMAT,
                ValidationCriterion.COMPLETENESS
            ],
            ValidationLevel.STRICT: [
                ValidationCriterion.NOT_NULL,
                ValidationCriterion.DATA_TYPE,
                ValidationCriterion.FORMAT,
                ValidationCriterion.RANGE,
                ValidationCriterion.COMPLETENESS,
                ValidationCriterion.CONSISTENCY
            ],
            ValidationLevel.COMPREHENSIVE: list(ValidationCriterion)
        }
    
    async def validate(
        self, 
        result: Any, 
        criteria: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        验证结果
        
        Args:
            result: 待验证的结果
            criteria: 验证标准配置
            
        Returns:
            验证结果字典
        """
        try:
            self.logger.info(f"开始结果验证，数据类型: {type(result).__name__}")
            
            # 解析验证标准
            validation_criteria = self._parse_criteria(criteria)
            
            # 执行验证
            issues = []
            for criterion in validation_criteria:
                criterion_issues = await self._validate_criterion(result, criterion, criteria)
                issues.extend(criterion_issues)
            
            # 计算质量分数
            quality_score = self._calculate_quality_score(result, issues)
            
            # 计算置信度
            confidence = self._calculate_confidence(result, issues)
            
            # 判断整体有效性
            is_valid = len([issue for issue in issues if issue.severity == "error"]) == 0
            
            validation_result = {
                "is_valid": is_valid,
                "confidence": confidence,
                "quality_score": quality_score,
                "issues": [
                    {
                        "criterion": issue.criterion.value,
                        "severity": issue.severity,
                        "message": issue.message,
                        "field_path": issue.field_path,
                        "expected_value": issue.expected_value,
                        "actual_value": issue.actual_value
                    } for issue in issues
                ],
                "validated_result": result,
                "metadata": {
                    "validation_time": "calculated",
                    "criteria_count": len(validation_criteria),
                    "issues_count": len(issues),
                    "error_count": len([i for i in issues if i.severity == "error"]),
                    "warning_count": len([i for i in issues if i.severity == "warning"]),
                    "data_size": self._calculate_data_size(result),
                    "validation_level": self._determine_validation_level(criteria)
                }
            }
            
            self.logger.info(
                f"结果验证完成: 有效性={is_valid}, 质量分数={quality_score:.2f}, "
                f"问题数={len(issues)}"
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"结果验证失败: {e}")
            raise ValueError(f"结果验证失败: {str(e)}")
    
    def _parse_criteria(self, criteria: Dict[str, Any] = None) -> List[ValidationCriterion]:
        """解析验证标准"""
        if not criteria:
            return self.default_criteria[ValidationLevel.STANDARD]
        
        # 如果指定了验证级别
        if "validation_level" in criteria:
            level_str = criteria["validation_level"].lower()
            for level in ValidationLevel:
                if level.value == level_str:
                    return self.default_criteria[level]
        
        # 如果指定了具体标准
        if "criteria" in criteria:
            criteria_list = []
            for criterion_str in criteria["criteria"]:
                for criterion in ValidationCriterion:
                    if criterion.value == criterion_str:
                        criteria_list.append(criterion)
                        break
            return criteria_list
        
        return self.default_criteria[ValidationLevel.STANDARD]
    
    async def _validate_criterion(
        self, 
        result: Any, 
        criterion: ValidationCriterion, 
        criteria_config: Dict[str, Any] = None
    ) -> List[ValidationIssue]:
        """验证单个标准"""
        issues = []
        
        if criterion == ValidationCriterion.NOT_NULL:
            issues.extend(self._validate_not_null(result))
        elif criterion == ValidationCriterion.DATA_TYPE:
            issues.extend(self._validate_data_type(result, criteria_config))
        elif criterion == ValidationCriterion.RANGE:
            issues.extend(self._validate_range(result, criteria_config))
        elif criterion == ValidationCriterion.FORMAT:
            issues.extend(self._validate_format(result, criteria_config))
        elif criterion == ValidationCriterion.COMPLETENESS:
            issues.extend(self._validate_completeness(result))
        elif criterion == ValidationCriterion.CONSISTENCY:
            issues.extend(self._validate_consistency(result))
        elif criterion == ValidationCriterion.BUSINESS_RULE:
            issues.extend(self._validate_business_rules(result, criteria_config))
        
        return issues
    
    def _validate_not_null(self, result: Any) -> List[ValidationIssue]:
        """验证非空"""
        issues = []
        
        if result is None:
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.NOT_NULL,
                severity="error",
                message="结果为空"
            ))
        elif isinstance(result, str) and not result.strip():
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.NOT_NULL,
                severity="error", 
                message="结果字符串为空"
            ))
        elif isinstance(result, (list, dict)) and len(result) == 0:
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.NOT_NULL,
                severity="warning",
                message="结果集合为空"
            ))
        
        return issues
    
    def _validate_data_type(
        self, 
        result: Any, 
        criteria_config: Dict[str, Any] = None
    ) -> List[ValidationIssue]:
        """验证数据类型"""
        issues = []
        
        if not criteria_config or "expected_type" not in criteria_config:
            return issues
        
        expected_type = criteria_config["expected_type"]
        actual_type = type(result).__name__
        
        if actual_type != expected_type:
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.DATA_TYPE,
                severity="error",
                message=f"数据类型不匹配",
                expected_value=expected_type,
                actual_value=actual_type
            ))
        
        return issues
    
    def _validate_range(
        self, 
        result: Any, 
        criteria_config: Dict[str, Any] = None
    ) -> List[ValidationIssue]:
        """验证数值范围"""
        issues = []
        
        if not criteria_config or not isinstance(result, (int, float)):
            return issues
        
        if "min_value" in criteria_config and result < criteria_config["min_value"]:
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.RANGE,
                severity="error",
                message=f"数值低于最小值",
                expected_value=f">= {criteria_config['min_value']}",
                actual_value=result
            ))
        
        if "max_value" in criteria_config and result > criteria_config["max_value"]:
            issues.append(ValidationIssue(
                criterion=ValidationCriterion.RANGE,
                severity="error",
                message=f"数值超过最大值",
                expected_value=f"<= {criteria_config['max_value']}",
                actual_value=result
            ))
        
        return issues
    
    def _validate_format(
        self, 
        result: Any, 
        criteria_config: Dict[str, Any] = None
    ) -> List[ValidationIssue]:
        """验证格式"""
        issues = []
        
        if isinstance(result, str):
            # 验证字符串格式
            if criteria_config and "pattern" in criteria_config:
                import re
                pattern = criteria_config["pattern"]
                if not re.match(pattern, result):
                    issues.append(ValidationIssue(
                        criterion=ValidationCriterion.FORMAT,
                        severity="warning",
                        message=f"字符串格式不匹配模式: {pattern}",
                        actual_value=result
                    ))
        
        elif isinstance(result, list):
            # 验证列表中每个元素的格式
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    # 检查字典的键是否符合命名规范
                    for key in item.keys():
                        if not isinstance(key, str) or not key.replace('_', '').isalnum():
                            issues.append(ValidationIssue(
                                criterion=ValidationCriterion.FORMAT,
                                severity="info",
                                message=f"字典键名格式建议优化: {key}",
                                field_path=f"[{i}].{key}"
                            ))
        
        return issues
    
    def _validate_completeness(self, result: Any) -> List[ValidationIssue]:
        """验证完整性"""
        issues = []
        
        if isinstance(result, dict):
            # 检查是否有空值
            empty_fields = [k for k, v in result.items() if v is None or v == ""]
            if empty_fields:
                issues.append(ValidationIssue(
                    criterion=ValidationCriterion.COMPLETENESS,
                    severity="warning",
                    message=f"发现空字段: {empty_fields}"
                ))
        
        elif isinstance(result, list):
            if len(result) == 0:
                issues.append(ValidationIssue(
                    criterion=ValidationCriterion.COMPLETENESS,
                    severity="warning",
                    message="结果列表为空"
                ))
            else:
                # 检查列表中的完整性
                for i, item in enumerate(result):
                    if item is None:
                        issues.append(ValidationIssue(
                            criterion=ValidationCriterion.COMPLETENESS,
                            severity="warning",
                            message=f"列表项为空",
                            field_path=f"[{i}]"
                        ))
        
        return issues
    
    def _validate_consistency(self, result: Any) -> List[ValidationIssue]:
        """验证一致性"""
        issues = []
        
        if isinstance(result, list) and len(result) > 1:
            # 检查列表项的结构一致性
            if all(isinstance(item, dict) for item in result):
                first_keys = set(result[0].keys()) if result else set()
                for i, item in enumerate(result[1:], 1):
                    item_keys = set(item.keys())
                    if item_keys != first_keys:
                        missing = first_keys - item_keys
                        extra = item_keys - first_keys
                        if missing or extra:
                            issues.append(ValidationIssue(
                                criterion=ValidationCriterion.CONSISTENCY,
                                severity="warning",
                                message=f"结构不一致: 缺少{list(missing)}, 多余{list(extra)}",
                                field_path=f"[{i}]"
                            ))
        
        return issues
    
    def _validate_business_rules(
        self, 
        result: Any, 
        criteria_config: Dict[str, Any] = None
    ) -> List[ValidationIssue]:
        """验证业务规则"""
        issues = []
        
        # 这里可以添加具体的业务规则验证
        # 例如：数值合理性、业务逻辑一致性等
        
        if isinstance(result, dict) and "amount" in result:
            amount = result["amount"]
            if isinstance(amount, (int, float)) and amount < 0:
                issues.append(ValidationIssue(
                    criterion=ValidationCriterion.BUSINESS_RULE,
                    severity="warning",
                    message="金额不能为负数",
                    field_path="amount",
                    actual_value=amount
                ))
        
        return issues
    
    def _calculate_quality_score(self, result: Any, issues: List[ValidationIssue]) -> float:
        """计算质量分数"""
        if not issues:
            return 1.0
        
        # 基于问题严重程度计算分数
        error_penalty = len([i for i in issues if i.severity == "error"]) * 0.3
        warning_penalty = len([i for i in issues if i.severity == "warning"]) * 0.1
        info_penalty = len([i for i in issues if i.severity == "info"]) * 0.05
        
        total_penalty = error_penalty + warning_penalty + info_penalty
        score = max(0.0, 1.0 - total_penalty)
        
        return round(score, 2)
    
    def _calculate_confidence(self, result: Any, issues: List[ValidationIssue]) -> float:
        """计算置信度"""
        base_confidence = 0.8
        
        # 基于数据大小调整置信度
        data_size = self._calculate_data_size(result)
        if data_size > 100:
            base_confidence += 0.1
        elif data_size < 10:
            base_confidence -= 0.1
        
        # 基于问题数量调整置信度
        error_count = len([i for i in issues if i.severity == "error"])
        if error_count > 0:
            base_confidence -= error_count * 0.15
        
        warning_count = len([i for i in issues if i.severity == "warning"])
        if warning_count > 0:
            base_confidence -= warning_count * 0.05
        
        return max(0.0, min(1.0, round(base_confidence, 2)))
    
    def _calculate_data_size(self, result: Any) -> int:
        """计算数据大小"""
        if isinstance(result, (list, dict)):
            return len(result)
        elif isinstance(result, str):
            return len(result)
        else:
            return 1
    
    def _determine_validation_level(self, criteria: Dict[str, Any] = None) -> str:
        """确定验证级别"""
        if not criteria:
            return ValidationLevel.STANDARD.value
        
        if "validation_level" in criteria:
            return criteria["validation_level"]
        
        if "criteria" in criteria:
            criteria_count = len(criteria["criteria"])
            if criteria_count <= 2:
                return ValidationLevel.BASIC.value
            elif criteria_count <= 4:
                return ValidationLevel.STANDARD.value
            elif criteria_count <= 6:
                return ValidationLevel.STRICT.value
            else:
                return ValidationLevel.COMPREHENSIVE.value
        
        return ValidationLevel.STANDARD.value


# 全局实例
result_validator_service = ResultValidatorService()