"""
错误处理系统测试
验证统一错误处理和前端适配功能
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.utils.error_validation import ParameterValidator, ValidationResult
from app.schemas.frontend_adapters import adapt_error_for_frontend
from app.middleware.error_handling import APIErrorHandler


class TestParameterValidator:
    """参数验证器测试"""

    def test_validate_required_fields_success(self):
        """测试必需字段验证成功"""
        data = {"field1": "value1", "field2": "value2"}
        required_fields = ["field1", "field2"]

        result = ParameterValidator.validate_required_fields(data, required_fields)
        assert result.is_valid is True
        assert result.error_info is None

    def test_validate_required_fields_failure(self):
        """测试必需字段验证失败"""
        data = {"field1": "value1"}
        required_fields = ["field1", "field2", "field3"]

        result = ParameterValidator.validate_required_fields(data, required_fields)
        assert result.is_valid is False
        assert result.error_info is not None
        assert "field2" in result.error_info.error_message
        assert "field3" in result.error_info.error_message

    def test_validate_uuid_success(self):
        """测试UUID验证成功"""
        valid_uuid = "12345678-1234-5678-9abc-123456789012"

        result = ParameterValidator.validate_uuid(valid_uuid, "test_id")
        assert result.is_valid is True

    def test_validate_uuid_failure(self):
        """测试UUID验证失败"""
        invalid_uuid = "not-a-uuid"

        result = ParameterValidator.validate_uuid(invalid_uuid, "test_id")
        assert result.is_valid is False
        assert "UUID格式" in result.error_info.error_message

    def test_validate_email_success(self):
        """测试邮箱验证成功"""
        valid_email = "test@example.com"

        result = ParameterValidator.validate_email(valid_email)
        assert result.is_valid is True

    def test_validate_email_failure(self):
        """测试邮箱验证失败"""
        invalid_email = "invalid-email"

        result = ParameterValidator.validate_email(invalid_email)
        assert result.is_valid is False
        assert "邮箱格式无效" in result.error_info.error_message

    def test_validate_string_length_success(self):
        """测试字符串长度验证成功"""
        valid_string = "test string"

        result = ParameterValidator.validate_string_length(
            valid_string, "test_field", 5, 20
        )
        assert result.is_valid is True

    def test_validate_string_length_too_short(self):
        """测试字符串长度过短"""
        short_string = "hi"

        result = ParameterValidator.validate_string_length(
            short_string, "test_field", 5, 20
        )
        assert result.is_valid is False
        assert "不能少于" in result.error_info.error_message

    def test_validate_string_length_too_long(self):
        """测试字符串长度过长"""
        long_string = "a" * 100

        result = ParameterValidator.validate_string_length(
            long_string, "test_field", 5, 20
        )
        assert result.is_valid is False
        assert "不能超过" in result.error_info.error_message

    def test_validate_numeric_range_success(self):
        """测试数值范围验证成功"""
        result = ParameterValidator.validate_numeric_range(
            10, "test_number", 5, 15
        )
        assert result.is_valid is True

    def test_validate_numeric_range_too_small(self):
        """测试数值过小"""
        result = ParameterValidator.validate_numeric_range(
            2, "test_number", 5, 15
        )
        assert result.is_valid is False
        assert "不能小于" in result.error_info.error_message

    def test_validate_numeric_range_too_large(self):
        """测试数值过大"""
        result = ParameterValidator.validate_numeric_range(
            20, "test_number", 5, 15
        )
        assert result.is_valid is False
        assert "不能大于" in result.error_info.error_message

    def test_validate_enum_value_success(self):
        """测试枚举值验证成功"""
        result = ParameterValidator.validate_enum_value(
            "option1", "test_enum", ["option1", "option2", "option3"]
        )
        assert result.is_valid is True

    def test_validate_enum_value_failure(self):
        """测试枚举值验证失败"""
        result = ParameterValidator.validate_enum_value(
            "invalid_option", "test_enum", ["option1", "option2", "option3"]
        )
        assert result.is_valid is False
        assert "值无效" in result.error_info.error_message

    def test_validate_sql_query_success(self):
        """测试SQL查询验证成功"""
        safe_sql = "SELECT * FROM users WHERE id = 1"

        result = ParameterValidator.validate_sql_query(safe_sql)
        assert result.is_valid is True

    def test_validate_sql_query_dangerous(self):
        """测试危险SQL查询"""
        dangerous_sql = "SELECT * FROM users; DROP TABLE users;"

        result = ParameterValidator.validate_sql_query(dangerous_sql)
        assert result.is_valid is False
        assert "危险操作" in result.error_info.error_message

    def test_validate_sql_query_non_select(self):
        """测试非SELECT查询"""
        non_select_sql = "UPDATE users SET name = 'test'"

        result = ParameterValidator.validate_sql_query(non_select_sql)
        assert result.is_valid is False
        assert "仅支持SELECT" in result.error_info.error_message


class TestFrontendErrorAdapter:
    """前端错误适配器测试"""

    def test_adapt_error_for_frontend(self):
        """测试前端错误适配"""
        error_info = adapt_error_for_frontend(
            error_message="测试错误",
            error_type="validation",
            error_code="test_error",
            details={"field": "test_field"}
        )

        assert error_info.error_code == "test_error"
        assert error_info.error_message == "测试错误"
        assert error_info.error_type == "validation"
        assert error_info.severity == "error"
        assert error_info.details == {"field": "test_field"}
        assert len(error_info.suggestions) > 0
        assert error_info.support_info is not None

    def test_error_display_info_structure(self):
        """测试错误显示信息结构"""
        error_info = adapt_error_for_frontend(
            error_message="数据库连接失败",
            error_type="system",
            error_code="database_connection_error"
        )

        # 验证结构完整性
        assert hasattr(error_info, 'error_code')
        assert hasattr(error_info, 'error_message')
        assert hasattr(error_info, 'user_friendly_message')
        assert hasattr(error_info, 'error_type')
        assert hasattr(error_info, 'severity')
        assert hasattr(error_info, 'suggestions')
        assert hasattr(error_info, 'support_info')

        # 验证用户友好消息不为空
        assert error_info.user_friendly_message != ""
        assert len(error_info.suggestions) > 0


class TestAPIErrorHandler:
    """API错误处理器测试"""

    def test_handle_validation_error(self):
        """测试验证错误处理"""
        mock_error = ValueError("Invalid parameter")

        response = APIErrorHandler.handle_validation_error(mock_error, "test_field")

        assert response.status_code == 400
        # 可以添加更多响应内容验证

    def test_handle_permission_error(self):
        """测试权限错误处理"""
        response = APIErrorHandler.handle_permission_error(
            user_id="user123",
            resource="template",
            action="delete"
        )

        assert response.status_code == 403

    def test_handle_rate_limit_error(self):
        """测试频率限制错误处理"""
        response = APIErrorHandler.handle_rate_limit_error(
            user_id="user123",
            limit_type="api_calls"
        )

        assert response.status_code == 429

    def test_handle_agent_error(self):
        """测试Agent错误处理"""
        mock_error = Exception("Agent service unavailable")

        response = APIErrorHandler.handle_agent_error(
            error=mock_error,
            agent_context={"task_id": "task123"}
        )

        assert response.status_code == 503


# 集成测试示例
class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_multiple_validation_errors(self):
        """测试多个验证错误的合并处理"""
        from app.utils.error_validation import ErrorResponseBuilder

        # 创建多个验证错误
        validation_results = [
            ValidationResult(False, adapt_error_for_frontend("错误1", "validation", "error1")),
            ValidationResult(False, adapt_error_for_frontend("错误2", "validation", "error2")),
            ValidationResult(True),  # 成功的验证
            ValidationResult(False, adapt_error_for_frontend("错误3", "validation", "error3"))
        ]

        combined_error = ErrorResponseBuilder.build_validation_error_response(validation_results)

        assert combined_error is not None
        assert "错误1" in combined_error.error_message
        assert "错误2" in combined_error.error_message
        assert "错误3" in combined_error.error_message
        assert combined_error.error_code == "multiple_validation_errors"


if __name__ == "__main__":
    # 运行简单测试
    test_validator = TestParameterValidator()
    print("运行参数验证器测试...")

    try:
        test_validator.test_validate_required_fields_success()
        test_validator.test_validate_uuid_success()
        test_validator.test_validate_email_success()
        print("✅ 基础验证测试通过")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

    test_adapter = TestFrontendErrorAdapter()
    print("运行前端适配器测试...")

    try:
        test_adapter.test_adapt_error_for_frontend()
        test_adapter.test_error_display_info_structure()
        print("✅ 前端适配器测试通过")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

    print("✅ 错误处理系统测试完成")