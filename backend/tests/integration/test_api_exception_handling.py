"""
测试API端点异常处理集成

验证API端点正确使用统一异常处理系统。
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    PlaceholderProcessingError,
    ReportGenerationError,
    ValidationError
)


class TestIntelligentPlaceholdersAPIExceptionHandling:
    """测试智能占位符API异常处理"""
    
    def setup_method(self):
        """设置测试"""
        self.client = TestClient(app)
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_analyze_placeholders_processing_error(self, mock_get_db, mock_get_current_user):
        """测试占位符分析处理错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟占位符处理器抛出异常
        with patch('app.api.endpoints.intelligent_placeholders.PlaceholderProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.extract_placeholders.side_effect = Exception("占位符解析失败")
            mock_processor_class.return_value = mock_processor
            
            response = self.client.post(
                "/api/v1/intelligent-placeholders/analyze",
                json={
                    "template_content": "测试模板{{统计:总数}}",
                    "analysis_options": {}
                }
            )
        
        # 验证响应
        assert response.status_code == 422
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "占位符分析失败" in response_data["message"]
        assert response_data["code"] == "PLACEHOLDER_PROCESSING_ERROR"
        assert "template_content_length" in response_data["details"]
    
    @patch('app.api.endpoints.intelligent_placeholders.deps.get_current_user')
    @patch('app.api.endpoints.intelligent_placeholders.deps.get_db')
    def test_field_matching_not_found_error(self, mock_get_db, mock_get_current_user):
        """测试字段匹配数据源未找到错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟数据源服务返回None
        with patch('app.api.endpoints.intelligent_placeholders.EnhancedDataSourceService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_data_source.return_value = None
            mock_service_class.return_value = mock_service
            
            response = self.client.post(
                "/api/v1/intelligent-placeholders/field-matching",
                json={
                    "placeholder_text": "{{统计:总数}}",
                    "placeholder_type": "统计",
                    "description": "总数统计",
                    "data_source_id": 999,
                    "matching_options": {}
                }
            )
        
        # 验证响应
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "数据源未找到" in response_data["message"]
        assert response_data["code"] == "NOT_FOUND_ERROR"
        assert response_data["details"]["resource"] == "数据源"
        assert response_data["details"]["identifier"] == "999"
    
    @patch('app.api.endpoints.intelligent_placeholders.deps.get_current_user')
    @patch('app.api.endpoints.intelligent_placeholders.deps.get_db')
    def test_generate_report_template_not_found(self, mock_get_db, mock_get_current_user):
        """测试智能报告生成模板未找到错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # 模板不存在
        mock_db.query.return_value = mock_query
        mock_get_db.return_value = mock_db
        
        response = self.client.post(
            "/api/v1/intelligent-placeholders/generate-report",
            json={
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "data_source_id": 1,
                "processing_config": {},
                "output_config": {}
            }
        )
        
        # 验证响应
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "模板未找到" in response_data["message"]
        assert response_data["code"] == "NOT_FOUND_ERROR"
        assert response_data["details"]["resource"] == "模板"


class TestReportGenerationAPIExceptionHandling:
    """测试报告生成API异常处理"""
    
    def setup_method(self):
        """设置测试"""
        self.client = TestClient(app)
    
    @patch('app.api.endpoints.report_generation.deps.get_current_active_user')
    @patch('app.api.endpoints.report_generation.deps.get_db')
    def test_generate_report_not_found_error(self, mock_get_db, mock_get_current_user):
        """测试报告生成资源未找到错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟报告服务抛出ValueError
        with patch('app.api.endpoints.report_generation.create_report_generation_service') as mock_create_service:
            mock_service = Mock()
            mock_service.generate_report.side_effect = ValueError("模板不存在")
            mock_create_service.return_value = mock_service
            
            response = self.client.post(
                "/api/v1/reports/generate?task_id=1&template_id=999&data_source_id=1"
            )
        
        # 验证响应
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "报告生成资源未找到" in response_data["message"]
        assert response_data["code"] == "NOT_FOUND_ERROR"
        assert "模板不存在" in response_data["details"]["error"]
    
    @patch('app.api.endpoints.report_generation.deps.get_current_active_user')
    @patch('app.api.endpoints.report_generation.deps.get_db')
    def test_generate_report_generation_error(self, mock_get_db, mock_get_current_user):
        """测试报告生成错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟报告服务抛出通用异常
        with patch('app.api.endpoints.report_generation.create_report_generation_service') as mock_create_service:
            mock_service = Mock()
            mock_service.generate_report.side_effect = RuntimeError("生成过程中发生错误")
            mock_create_service.return_value = mock_service
            
            response = self.client.post(
                "/api/v1/reports/generate?task_id=1&template_id=1&data_source_id=1"
            )
        
        # 验证响应
        assert response.status_code == 500
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "报告生成失败" in response_data["message"]
        assert response_data["code"] == "REPORT_GENERATION_ERROR"
        assert response_data["details"]["template_id"] == "1"
        assert response_data["details"]["task_id"] == 1
    
    @patch('app.api.endpoints.report_generation.deps.get_current_active_user')
    @patch('app.api.endpoints.report_generation.deps.get_db')
    def test_validate_report_configuration_error(self, mock_get_db, mock_get_current_user):
        """测试报告配置验证错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟报告服务抛出通用异常
        with patch('app.api.endpoints.report_generation.create_report_generation_service') as mock_create_service:
            mock_service = Mock()
            mock_service.validate_report_configuration.side_effect = Exception("配置验证失败")
            mock_create_service.return_value = mock_service
            
            response = self.client.post(
                "/api/v1/reports/validate?template_id=1&data_source_id=1"
            )
        
        # 验证响应
        assert response.status_code == 422
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "报告配置验证失败" in response_data["message"]
        assert response_data["code"] == "VALIDATION_ERROR"
        assert response_data["details"]["template_id"] == 1
        assert response_data["details"]["data_source_id"] == 1


class TestTemplatesAPIExceptionHandling:
    """测试模板API异常处理"""
    
    def setup_method(self):
        """设置测试"""
        self.client = TestClient(app)
    
    @patch('app.api.endpoints.templates.deps.get_current_user')
    @patch('app.api.endpoints.templates.deps.get_db')
    def test_read_template_not_found(self, mock_get_db, mock_get_current_user):
        """测试读取模板未找到错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟CRUD返回None
        with patch('app.api.endpoints.templates.crud.template.get') as mock_get:
            mock_get.return_value = None
            
            response = self.client.get(
                "/api/v1/templates/123e4567-e89b-12d3-a456-426614174000"
            )
        
        # 验证响应
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "模板未找到" in response_data["message"]
        assert response_data["code"] == "NOT_FOUND_ERROR"
        assert response_data["details"]["resource"] == "模板"
    
    @patch('app.api.endpoints.templates.deps.get_current_user')
    @patch('app.api.endpoints.templates.deps.get_db')
    def test_read_template_authorization_error(self, mock_get_db, mock_get_current_user):
        """测试读取模板权限错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟CRUD返回其他用户的私有模板
        mock_template = Mock()
        mock_template.is_public = False
        mock_template.user_id = 2  # 不同的用户ID
        
        with patch('app.api.endpoints.templates.crud.template.get') as mock_get:
            mock_get.return_value = mock_template
            
            response = self.client.get(
                "/api/v1/templates/123e4567-e89b-12d3-a456-426614174000"
            )
        
        # 验证响应
        assert response.status_code == 403
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "无权限访问此模板" in response_data["message"]
        assert response_data["code"] == "AUTHORIZATION_ERROR"
        assert response_data["details"]["user_id"] == 1
    
    @patch('app.api.endpoints.templates.deps.get_current_user')
    @patch('app.api.endpoints.templates.deps.get_db')
    def test_update_template_not_found(self, mock_get_db, mock_get_current_user):
        """测试更新模板未找到错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟CRUD返回None
        with patch('app.api.endpoints.templates.crud.template.get') as mock_get:
            mock_get.return_value = None
            
            response = self.client.put(
                "/api/v1/templates/123e4567-e89b-12d3-a456-426614174000",
                json={
                    "name": "更新的模板",
                    "description": "更新的描述"
                }
            )
        
        # 验证响应
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "模板未找到" in response_data["message"]
        assert response_data["code"] == "NOT_FOUND_ERROR"
    
    @patch('app.api.endpoints.templates.deps.get_current_user')
    @patch('app.api.endpoints.templates.deps.get_db')
    def test_delete_template_authorization_error(self, mock_get_db, mock_get_current_user):
        """测试删除模板权限错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 模拟CRUD返回其他用户的模板
        mock_template = Mock()
        mock_template.user_id = 2  # 不同的用户ID
        
        with patch('app.api.endpoints.templates.crud.template.get') as mock_get:
            mock_get.return_value = mock_template
            
            response = self.client.delete(
                "/api/v1/templates/123e4567-e89b-12d3-a456-426614174000"
            )
        
        # 验证响应
        assert response.status_code == 403
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "无权限删除此模板" in response_data["message"]
        assert response_data["code"] == "AUTHORIZATION_ERROR"


class TestGlobalExceptionHandling:
    """测试全局异常处理"""
    
    def setup_method(self):
        """设置测试"""
        self.client = TestClient(app)
    
    def test_404_endpoint_not_found(self):
        """测试404端点未找到"""
        response = self.client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "404" in response_data["message"]
        assert response_data["code"] == "HTTP_404"
    
    def test_405_method_not_allowed(self):
        """测试405方法不允许"""
        # 尝试对只支持GET的端点使用POST
        response = self.client.post("/api/v1/templates/")
        
        # 注意：这个测试可能需要根据实际的路由配置调整
        # 如果模板端点支持POST，则需要选择其他只支持GET的端点
        assert response.status_code in [405, 422]  # 可能是405或422，取决于FastAPI的处理
    
    @patch('app.api.endpoints.templates.deps.get_current_user')
    @patch('app.api.endpoints.templates.deps.get_db')
    def test_422_validation_error(self, mock_get_db, mock_get_current_user):
        """测试422验证错误"""
        # 设置模拟
        mock_user = Mock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=Session)
        
        # 发送无效的JSON数据
        response = self.client.post(
            "/api/v1/templates/",
            json={
                # 缺少必需的字段
                "description": "测试描述"
                # 缺少name字段
            }
        )
        
        assert response.status_code == 422
        response_data = response.json()
        
        assert response_data["error"] is True
        assert "验证失败" in response_data["message"] or "validation" in response_data["message"].lower()
        assert "VALIDATION_ERROR" in response_data["code"]


class TestExceptionResponseFormat:
    """测试异常响应格式"""
    
    def setup_method(self):
        """设置测试"""
        self.client = TestClient(app)
    
    def test_exception_response_structure(self):
        """测试异常响应结构"""
        # 触发一个404错误
        response = self.client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
        response_data = response.json()
        
        # 验证响应结构
        required_fields = ["error", "message", "code", "details", "timestamp"]
        for field in required_fields:
            assert field in response_data, f"Missing field: {field}"
        
        # 验证字段类型
        assert isinstance(response_data["error"], bool)
        assert isinstance(response_data["message"], str)
        assert isinstance(response_data["code"], str)
        assert isinstance(response_data["details"], dict)
        # timestamp可能为None
        
        # 验证error字段为True（表示这是一个错误响应）
        assert response_data["error"] is True
    
    def test_different_exceptions_same_format(self):
        """测试不同异常使用相同的响应格式"""
        # 收集不同类型的错误响应
        responses = []
        
        # 404错误
        responses.append(self.client.get("/api/v1/nonexistent"))
        
        # 422验证错误（发送无效JSON）
        responses.append(self.client.post("/api/v1/templates/", json={}))
        
        # 验证所有响应都有相同的基本结构
        for response in responses:
            response_data = response.json()
            
            required_fields = ["error", "message", "code", "details", "timestamp"]
            for field in required_fields:
                assert field in response_data
            
            assert response_data["error"] is True
            assert len(response_data["message"]) > 0
            assert len(response_data["code"]) > 0