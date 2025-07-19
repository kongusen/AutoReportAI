"""
测试统一异常处理系统

验证所有自定义异常类的功能和异常处理中间件的正确性。
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    PlaceholderProcessingError,
    FieldMatchingError,
    PlaceholderAdapterError,
    ReportGenerationError,
    ReportCompositionError,
    ReportQualityError,
    DataRetrievalError,
    DataAnalysisError,
    ETLProcessingError,
    LLMServiceError,
    ContentGenerationError,
    ChartGenerationError,
    NotificationError,
    EmailServiceError,
    WebSocketError,
    create_http_exception
)


class TestAppException:
    """测试基础应用异常类"""
    
    def test_app_exception_creation(self):
        """测试应用异常创建"""
        exc = AppException(
            message="测试错误",
            code="TEST_ERROR",
            status_code=400,
            details={"key": "value"}
        )
        
        assert exc.message == "测试错误"
        assert exc.code == "TEST_ERROR"
        assert exc.status_code == 400
        assert exc.details == {"key": "value"}
        assert str(exc) == "测试错误"
    
    def test_app_exception_defaults(self):
        """测试应用异常默认值"""
        exc = AppException(message="测试", code="TEST")
        
        assert exc.status_code == 400
        assert exc.details == {}


class TestValidationError:
    """测试验证异常"""
    
    def test_validation_error_creation(self):
        """测试验证异常创建"""
        exc = ValidationError(
            message="字段验证失败",
            field="email",
            details={"pattern": "email"}
        )
        
        assert exc.message == "字段验证失败"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.details["field"] == "email"
        assert exc.details["pattern"] == "email"
    
    def test_validation_error_without_field(self):
        """测试不带字段的验证异常"""
        exc = ValidationError(message="验证失败")
        
        assert exc.message == "验证失败"
        assert "field" not in exc.details


class TestAuthenticationError:
    """测试认证异常"""
    
    def test_authentication_error_creation(self):
        """测试认证异常创建"""
        exc = AuthenticationError(
            message="令牌无效",
            details={"token_type": "JWT"}
        )
        
        assert exc.message == "令牌无效"
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.details["token_type"] == "JWT"
    
    def test_authentication_error_default_message(self):
        """测试认证异常默认消息"""
        exc = AuthenticationError()
        
        assert exc.message == "认证失败"


class TestAuthorizationError:
    """测试授权异常"""
    
    def test_authorization_error_creation(self):
        """测试授权异常创建"""
        exc = AuthorizationError(
            message="无权限访问资源",
            details={"resource": "template", "action": "read"}
        )
        
        assert exc.message == "无权限访问资源"
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.details["resource"] == "template"
    
    def test_authorization_error_default_message(self):
        """测试授权异常默认消息"""
        exc = AuthorizationError()
        
        assert exc.message == "权限不足"


class TestNotFoundError:
    """测试资源未找到异常"""
    
    def test_not_found_error_creation(self):
        """测试资源未找到异常创建"""
        exc = NotFoundError(
            resource="用户",
            identifier=123,
            details={"search_field": "id"}
        )
        
        assert exc.message == "用户未找到: 123"
        assert exc.code == "NOT_FOUND_ERROR"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.details["resource"] == "用户"
        assert exc.details["identifier"] == "123"
        assert exc.details["search_field"] == "id"
    
    def test_not_found_error_without_identifier(self):
        """测试不带标识符的资源未找到异常"""
        exc = NotFoundError(resource="模板")
        
        assert exc.message == "模板未找到"
        assert exc.details["resource"] == "模板"
        assert "identifier" not in exc.details


class TestConflictError:
    """测试资源冲突异常"""
    
    def test_conflict_error_creation(self):
        """测试资源冲突异常创建"""
        exc = ConflictError(
            message="用户名已存在",
            resource="用户",
            details={"username": "test_user"}
        )
        
        assert exc.message == "用户名已存在"
        assert exc.code == "CONFLICT_ERROR"
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.details["resource"] == "用户"
        assert exc.details["username"] == "test_user"


class TestDatabaseError:
    """测试数据库异常"""
    
    def test_database_error_creation(self):
        """测试数据库异常创建"""
        exc = DatabaseError(
            message="连接超时",
            operation="SELECT",
            details={"table": "users"}
        )
        
        assert exc.message == "连接超时"
        assert exc.code == "DATABASE_ERROR"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.details["operation"] == "SELECT"
        assert exc.details["table"] == "users"
    
    def test_database_error_default_message(self):
        """测试数据库异常默认消息"""
        exc = DatabaseError()
        
        assert exc.message == "数据库操作失败"


class TestExternalServiceError:
    """测试外部服务异常"""
    
    def test_external_service_error_creation(self):
        """测试外部服务异常创建"""
        exc = ExternalServiceError(
            service="OpenAI API",
            message="请求限制",
            details={"rate_limit": "60/min"}
        )
        
        assert exc.message == "OpenAI API: 请求限制"
        assert exc.code == "EXTERNAL_SERVICE_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details["service"] == "OpenAI API"
        assert exc.details["rate_limit"] == "60/min"


class TestServiceSpecificExceptions:
    """测试服务特定异常"""
    
    def test_placeholder_processing_error(self):
        """测试占位符处理异常"""
        exc = PlaceholderProcessingError(
            message="占位符解析失败",
            placeholder_type="统计",
            details={"position": 10}
        )
        
        assert exc.message == "占位符解析失败"
        assert exc.code == "PLACEHOLDER_PROCESSING_ERROR"
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.details["placeholder_type"] == "统计"
        assert exc.details["position"] == 10
    
    def test_field_matching_error(self):
        """测试字段匹配异常"""
        exc = FieldMatchingError(
            message="字段匹配失败",
            field_name="total_count",
            details={"confidence": 0.3}
        )
        
        assert exc.message == "字段匹配失败"
        assert exc.code == "FIELD_MATCHING_ERROR"
        assert exc.details["field_name"] == "total_count"
        assert exc.details["confidence"] == 0.3
    
    def test_report_generation_error(self):
        """测试报告生成异常"""
        exc = ReportGenerationError(
            message="报告生成失败",
            template_id="123",
            details={"step": "content_generation"}
        )
        
        assert exc.message == "报告生成失败"
        assert exc.code == "REPORT_GENERATION_ERROR"
        assert exc.details["template_id"] == "123"
        assert exc.details["step"] == "content_generation"
    
    def test_data_retrieval_error(self):
        """测试数据检索异常"""
        exc = DataRetrievalError(
            message="数据查询失败",
            data_source="MySQL",
            details={"query": "SELECT * FROM complaints"}
        )
        
        assert exc.message == "数据查询失败"
        assert exc.code == "DATA_RETRIEVAL_ERROR"
        assert exc.details["data_source"] == "MySQL"
        assert exc.details["query"] == "SELECT * FROM complaints"
    
    def test_llm_service_error(self):
        """测试LLM服务异常"""
        exc = LLMServiceError(
            message="LLM调用失败",
            provider="OpenAI",
            details={"model": "gpt-4", "error_code": "rate_limit"}
        )
        
        assert exc.message == "LLM调用失败"
        assert exc.code == "LLM_SERVICE_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details["provider"] == "OpenAI"
        assert exc.details["model"] == "gpt-4"
    
    def test_notification_error(self):
        """测试通知服务异常"""
        exc = NotificationError(
            message="通知发送失败",
            notification_type="email",
            details={"recipient": "user@example.com"}
        )
        
        assert exc.message == "通知发送失败"
        assert exc.code == "NOTIFICATION_ERROR"
        assert exc.details["notification_type"] == "email"
        assert exc.details["recipient"] == "user@example.com"


class TestCreateHttpException:
    """测试HTTP异常转换函数"""
    
    def test_create_http_exception(self):
        """测试将应用异常转换为HTTP异常"""
        app_exc = ValidationError(
            message="字段验证失败",
            field="email",
            details={"pattern": "email"}
        )
        
        http_exc = create_http_exception(app_exc)
        
        assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert http_exc.detail["message"] == "字段验证失败"
        assert http_exc.detail["code"] == "VALIDATION_ERROR"
        assert http_exc.detail["details"]["field"] == "email"
        assert http_exc.detail["details"]["pattern"] == "email"


class TestExceptionInheritance:
    """测试异常继承关系"""
    
    def test_all_exceptions_inherit_from_app_exception(self):
        """测试所有自定义异常都继承自AppException"""
        exception_classes = [
            ValidationError,
            AuthenticationError,
            AuthorizationError,
            NotFoundError,
            ConflictError,
            DatabaseError,
            ExternalServiceError,
            PlaceholderProcessingError,
            FieldMatchingError,
            PlaceholderAdapterError,
            ReportGenerationError,
            ReportCompositionError,
            ReportQualityError,
            DataRetrievalError,
            DataAnalysisError,
            ETLProcessingError,
            LLMServiceError,
            ContentGenerationError,
            ChartGenerationError,
            NotificationError,
            EmailServiceError,
            WebSocketError,
        ]
        
        for exc_class in exception_classes:
            assert issubclass(exc_class, AppException)
            assert issubclass(exc_class, Exception)
    
    def test_exception_instantiation(self):
        """测试所有异常类都可以正常实例化"""
        exception_classes = [
            (ValidationError, {"message": "test"}),
            (AuthenticationError, {}),
            (AuthorizationError, {}),
            (NotFoundError, {"resource": "test"}),
            (ConflictError, {"message": "test"}),
            (DatabaseError, {}),
            (ExternalServiceError, {"service": "test"}),
            (PlaceholderProcessingError, {"message": "test"}),
            (FieldMatchingError, {"message": "test"}),
            (PlaceholderAdapterError, {"message": "test"}),
            (ReportGenerationError, {"message": "test"}),
            (ReportCompositionError, {"message": "test"}),
            (ReportQualityError, {"message": "test"}),
            (DataRetrievalError, {"message": "test"}),
            (DataAnalysisError, {"message": "test"}),
            (ETLProcessingError, {"message": "test"}),
            (LLMServiceError, {"message": "test"}),
            (ContentGenerationError, {"message": "test"}),
            (ChartGenerationError, {"message": "test"}),
            (NotificationError, {"message": "test"}),
            (EmailServiceError, {"message": "test"}),
            (WebSocketError, {"message": "test"}),
        ]
        
        for exc_class, kwargs in exception_classes:
            exc = exc_class(**kwargs)
            assert isinstance(exc, AppException)
            assert isinstance(exc, Exception)
            assert hasattr(exc, 'message')
            assert hasattr(exc, 'code')
            assert hasattr(exc, 'status_code')
            assert hasattr(exc, 'details')