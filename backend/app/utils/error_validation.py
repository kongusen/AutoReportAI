"""
错误验证和处理工具
提供统一的参数验证和错误处理功能
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import UUID
from datetime import datetime
from pydantic import ValidationError

from app.schemas.frontend_adapters import adapt_error_for_frontend, ErrorDisplayInfo

logger = logging.getLogger(__name__)


class ValidationResult:
    """验证结果封装"""
    def __init__(self, is_valid: bool, error_info: Optional[ErrorDisplayInfo] = None):
        self.is_valid = is_valid
        self.error_info = error_info

    @property
    def is_error(self) -> bool:
        return not self.is_valid


class ParameterValidator:
    """参数验证器"""

    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
        """验证必需字段"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]

        if missing_fields:
            error_info = adapt_error_for_frontend(
                error_message=f"缺少必需参数: {', '.join(missing_fields)}",
                error_type="validation",
                error_code="missing_required_fields",
                details={"missing_fields": missing_fields, "provided_fields": list(data.keys())}
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_uuid(value: str, field_name: str = "ID") -> ValidationResult:
        """验证UUID格式"""
        try:
            UUID(value)
            return ValidationResult(True)
        except (ValueError, TypeError):
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 格式无效，应为UUID格式",
                error_type="validation",
                error_code="invalid_uuid_format",
                details={"field_name": field_name, "provided_value": value}
            )
            return ValidationResult(False, error_info)

    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """验证邮箱格式"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            error_info = adapt_error_for_frontend(
                error_message="邮箱格式无效",
                error_type="validation",
                error_code="invalid_email_format",
                details={"provided_email": email}
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_string_length(
        value: str,
        field_name: str,
        min_length: int = 0,
        max_length: int = 1000
    ) -> ValidationResult:
        """验证字符串长度"""
        if len(value) < min_length:
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 长度不能少于 {min_length} 个字符",
                error_type="validation",
                error_code="string_too_short",
                details={
                    "field_name": field_name,
                    "min_length": min_length,
                    "actual_length": len(value)
                }
            )
            return ValidationResult(False, error_info)

        if len(value) > max_length:
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 长度不能超过 {max_length} 个字符",
                error_type="validation",
                error_code="string_too_long",
                details={
                    "field_name": field_name,
                    "max_length": max_length,
                    "actual_length": len(value)
                }
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_numeric_range(
        value: Union[int, float],
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> ValidationResult:
        """验证数值范围"""
        if min_value is not None and value < min_value:
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 不能小于 {min_value}",
                error_type="validation",
                error_code="value_too_small",
                details={
                    "field_name": field_name,
                    "min_value": min_value,
                    "actual_value": value
                }
            )
            return ValidationResult(False, error_info)

        if max_value is not None and value > max_value:
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 不能大于 {max_value}",
                error_type="validation",
                error_code="value_too_large",
                details={
                    "field_name": field_name,
                    "max_value": max_value,
                    "actual_value": value
                }
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_enum_value(
        value: str,
        field_name: str,
        allowed_values: List[str]
    ) -> ValidationResult:
        """验证枚举值"""
        if value not in allowed_values:
            error_info = adapt_error_for_frontend(
                error_message=f"{field_name} 值无效，允许的值: {', '.join(allowed_values)}",
                error_type="validation",
                error_code="invalid_enum_value",
                details={
                    "field_name": field_name,
                    "allowed_values": allowed_values,
                    "provided_value": value
                }
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_cron_expression(cron_expr: str) -> ValidationResult:
        """验证Cron表达式格式"""
        # 简单的Cron表达式验证
        cron_parts = cron_expr.split()

        if len(cron_parts) not in [5, 6]:
            error_info = adapt_error_for_frontend(
                error_message="Cron表达式格式无效，应包含5或6个部分",
                error_type="validation",
                error_code="invalid_cron_format",
                details={"provided_cron": cron_expr, "parts_count": len(cron_parts)}
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)

    @staticmethod
    def validate_sql_query(sql_query: str) -> ValidationResult:
        """验证SQL查询基本格式"""
        # 基础SQL注入防护检查
        dangerous_patterns = [
            r';\s*(DROP|DELETE|UPDATE|INSERT)\s',
            r'UNION\s+SELECT',
            r'--\s*$',
            r'/\*.*\*/',
            r'xp_cmdshell',
            r'sp_executesql'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, sql_query.upper()):
                error_info = adapt_error_for_frontend(
                    error_message="SQL查询包含潜在的危险操作",
                    error_type="security",
                    error_code="dangerous_sql_pattern",
                    details={"detected_pattern": pattern}
                )
                return ValidationResult(False, error_info)

        # 检查基本SELECT格式
        if not re.search(r'^\s*SELECT\s', sql_query.upper().strip()):
            error_info = adapt_error_for_frontend(
                error_message="仅支持SELECT查询语句",
                error_type="validation",
                error_code="unsupported_sql_operation",
                details={"query_start": sql_query[:50]}
            )
            return ValidationResult(False, error_info)

        return ValidationResult(True)


class BusinessRuleValidator:
    """业务规则验证器"""

    @staticmethod
    def validate_template_placeholder_relationship(
        template_id: str,
        placeholder_name: str,
        db_session
    ) -> ValidationResult:
        """验证模板和占位符的关系"""
        # 这里可以添加数据库查询验证逻辑
        # 暂时返回成功，实际实现时需要查询数据库
        return ValidationResult(True)

    @staticmethod
    def validate_user_permission(
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: str = None
    ) -> ValidationResult:
        """验证用户权限"""
        # 这里可以添加权限检查逻辑
        # 暂时返回成功，实际实现时需要检查用户权限
        return ValidationResult(True)

    @staticmethod
    def validate_data_source_access(
        user_id: str,
        data_source_id: str,
        db_session
    ) -> ValidationResult:
        """验证数据源访问权限"""
        # 这里可以添加数据源访问权限检查
        # 暂时返回成功，实际实现时需要查询数据库
        return ValidationResult(True)


class ErrorResponseBuilder:
    """错误响应构建器"""

    @staticmethod
    def build_validation_error_response(validation_results: List[ValidationResult]) -> Optional[ErrorDisplayInfo]:
        """构建验证错误响应"""
        error_results = [result for result in validation_results if result.is_error]

        if not error_results:
            return None

        # 合并多个验证错误
        error_messages = []
        error_details = []

        for result in error_results:
            if result.error_info:
                error_messages.append(result.error_info.error_message)
                if result.error_info.details:
                    error_details.append(result.error_info.details)

        combined_error = adapt_error_for_frontend(
            error_message="; ".join(error_messages),
            error_type="validation",
            error_code="multiple_validation_errors",
            details={
                "error_count": len(error_results),
                "individual_errors": error_details
            }
        )

        return combined_error

    @staticmethod
    def build_business_rule_error_response(rule_name: str, details: Dict[str, Any]) -> ErrorDisplayInfo:
        """构建业务规则错误响应"""
        return adapt_error_for_frontend(
            error_message=f"违反业务规则: {rule_name}",
            error_type="business_rule",
            error_code="business_rule_violation",
            details=details
        )


# 验证装饰器
def validate_parameters(
    required_fields: List[str] = None,
    validation_rules: List[Callable[[Dict[str, Any]], ValidationResult]] = None
):
    """参数验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从kwargs中提取request数据
            request_data = kwargs.get('request', {})
            if hasattr(request_data, 'dict'):
                request_data = request_data.dict()

            validation_results = []

            # 验证必需字段
            if required_fields:
                result = ParameterValidator.validate_required_fields(request_data, required_fields)
                validation_results.append(result)

            # 执行自定义验证规则
            if validation_rules:
                for rule in validation_rules:
                    result = rule(request_data)
                    validation_results.append(result)

            # 检查验证结果
            error_response = ErrorResponseBuilder.build_validation_error_response(validation_results)
            if error_response:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=error_response.user_friendly_message
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator