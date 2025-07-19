"""
测试异常处理中间件

验证全局异常处理中间件的正确性和响应格式。
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.exceptions import (
    AppException,
    ValidationError as AppValidationError,
    NotFoundError,
    DatabaseError
)
from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    pydantic_validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
    setup_exception_handlers
)


class TestAppExceptionHandler:
    """测试应用异常处理器"""
    
    @pytest.mark.asyncio
    async def test_app_exception_handler(self):
        """测试应用异常处理器"""
        # 创建模拟请求
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        request.state.timestamp = "2024-01-01T10:00:00Z"
        
        # 创建应用异常
        exc = NotFoundError(
            resource="用户",
            identifier=123,
            details={"search_field": "id"}
        )
        
        # 调用异常处理器
        response = await app_exception_handler(request, exc)
        
        # 验证响应
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # 验证响应内容
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "用户未找到: 123"
        assert response_data["code"] == "NOT_FOUND_ERROR"
        assert response_data["details"]["resource"] == "用户"
        assert response_data["details"]["identifier"] == "123"
        assert response_data["timestamp"] == "2024-01-01T10:00:00Z"
    
    @pytest.mark.asyncio
    async def test_app_exception_handler_without_timestamp(self):
        """测试没有时间戳的应用异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "POST"
        request.state = Mock()
        # 没有timestamp属性
        
        exc = AppValidationError(
            message="验证失败",
            field="email"
        )
        
        response = await app_exception_handler(request, exc)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["timestamp"] is None


class TestHttpExceptionHandler:
    """测试HTTP异常处理器"""
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """测试HTTP异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        request.state.timestamp = "2024-01-01T10:00:00Z"
        
        exc = StarletteHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
        
        response = await http_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "Resource not found"
        assert response_data["code"] == "HTTP_404"
        assert response_data["details"] == {}
        assert response_data["timestamp"] == "2024-01-01T10:00:00Z"


class TestValidationExceptionHandler:
    """测试验证异常处理器"""
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """测试请求验证异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "POST"
        request.state = Mock()
        request.state.timestamp = "2024-01-01T10:00:00Z"
        
        # 创建验证错误
        validation_errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None
            },
            {
                "loc": ("body", "age"),
                "msg": "ensure this value is greater than 0",
                "type": "value_error.number.not_gt",
                "input": -1
            }
        ]
        
        exc = RequestValidationError(validation_errors)
        
        response = await validation_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "请求数据验证失败"
        assert response_data["code"] == "VALIDATION_ERROR"
        assert len(response_data["details"]["validation_errors"]) == 2
        
        # 验证第一个错误
        first_error = response_data["details"]["validation_errors"][0]
        assert first_error["field"] == "body -> email"
        assert first_error["message"] == "field required"
        assert first_error["type"] == "value_error.missing"
        
        # 验证第二个错误
        second_error = response_data["details"]["validation_errors"][1]
        assert second_error["field"] == "body -> age"
        assert second_error["message"] == "ensure this value is greater than 0"
        assert second_error["input"] == -1


class TestPydanticValidationExceptionHandler:
    """测试Pydantic验证异常处理器"""
    
    @pytest.mark.asyncio
    async def test_pydantic_validation_exception_handler(self):
        """测试Pydantic验证异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "POST"
        request.state = Mock()
        
        # 创建Pydantic验证错误
        validation_errors = [
            {
                "loc": ("email",),
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]
        
        exc = ValidationError(validation_errors, Mock)
        
        response = await pydantic_validation_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "数据验证失败"
        assert response_data["code"] == "PYDANTIC_VALIDATION_ERROR"
        assert "validation_errors" in response_data["details"]


class TestSqlAlchemyExceptionHandler:
    """测试SQLAlchemy异常处理器"""
    
    @pytest.mark.asyncio
    async def test_sqlalchemy_exception_handler(self):
        """测试SQLAlchemy异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "POST"
        request.state = Mock()
        
        # 创建SQLAlchemy异常
        exc = SQLAlchemyError("Database connection failed")
        
        response = await sqlalchemy_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "数据库操作失败"
        assert response_data["code"] == "DATABASE_ERROR"
        assert response_data["details"]["exception_type"] == "SQLAlchemyError"
        assert response_data["details"]["original_message"] == "Database connection failed"


class TestGeneralExceptionHandler:
    """测试通用异常处理器"""
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """测试通用异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        
        # 创建通用异常
        exc = ValueError("Unexpected error occurred")
        
        with patch('app.core.exception_handlers.logger') as mock_logger:
            mock_logger.level = 30  # WARNING level
            
            response = await general_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["error"] is True
        assert response_data["message"] == "服务器内部错误"
        assert response_data["code"] == "INTERNAL_SERVER_ERROR"
        assert response_data["details"]["exception_type"] == "ValueError"
        assert response_data["details"]["debug_message"] is None  # 不在DEBUG模式
    
    @pytest.mark.asyncio
    async def test_general_exception_handler_debug_mode(self):
        """测试调试模式下的通用异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        
        exc = ValueError("Debug error message")
        
        with patch('app.core.exception_handlers.logger') as mock_logger:
            mock_logger.level = 10  # DEBUG level
            
            response = await general_exception_handler(request, exc)
        
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert response_data["details"]["debug_message"] == "Debug error message"


class TestSetupExceptionHandlers:
    """测试异常处理器设置"""
    
    def test_setup_exception_handlers(self):
        """测试异常处理器设置函数"""
        # 创建模拟应用
        mock_app = Mock()
        mock_app.add_exception_handler = Mock()
        
        # 调用设置函数
        setup_exception_handlers(mock_app)
        
        # 验证所有异常处理器都被添加
        expected_calls = [
            (AppException, app_exception_handler),
            (StarletteHTTPException, http_exception_handler),
            (RequestValidationError, validation_exception_handler),
            (ValidationError, pydantic_validation_exception_handler),
            (SQLAlchemyError, sqlalchemy_exception_handler),
            (Exception, general_exception_handler),
        ]
        
        assert mock_app.add_exception_handler.call_count == len(expected_calls)
        
        # 验证调用参数
        for i, (exc_type, handler) in enumerate(expected_calls):
            call_args = mock_app.add_exception_handler.call_args_list[i]
            assert call_args[0][0] == exc_type
            assert call_args[0][1] == handler


class TestExceptionHandlerIntegration:
    """测试异常处理器集成"""
    
    @pytest.mark.asyncio
    async def test_exception_chain_handling(self):
        """测试异常链处理"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        
        # 测试应用异常优先于通用异常
        app_exc = NotFoundError(resource="测试资源", identifier="123")
        
        # 应用异常处理器应该处理AppException及其子类
        response = await app_exception_handler(request, app_exc)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # 通用异常处理器应该处理其他异常
        general_exc = RuntimeError("运行时错误")
        response = await general_exception_handler(request, general_exc)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_response_format_consistency(self):
        """测试响应格式一致性"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"
        request.state = Mock()
        request.state.timestamp = "2024-01-01T10:00:00Z"
        
        # 测试不同异常处理器的响应格式一致性
        handlers_and_exceptions = [
            (app_exception_handler, NotFoundError(resource="测试")),
            (http_exception_handler, StarletteHTTPException(404, "Not found")),
            (general_exception_handler, RuntimeError("Runtime error")),
        ]
        
        for handler, exc in handlers_and_exceptions:
            response = await handler(request, exc)
            
            content = response.body.decode()
            import json
            response_data = json.loads(content)
            
            # 验证所有响应都有相同的基本结构
            required_fields = ["error", "message", "code", "details", "timestamp"]
            for field in required_fields:
                assert field in response_data
            
            assert response_data["error"] is True
            assert isinstance(response_data["message"], str)
            assert isinstance(response_data["code"], str)
            assert isinstance(response_data["details"], dict)