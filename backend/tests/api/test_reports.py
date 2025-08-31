"""
报告生成API端点测试
"""
import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from app.models.user import User
from app.models.template import Template
from app.models.data_source import DataSource
from app.models.report_history import ReportHistory
from app.models.task import Task


class TestReportsAPI:
    """报告生成API测试类"""
    
    @pytest.mark.asyncio
    async def test_get_reports_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_task: Task,
        sample_report: ReportHistory
    ):
        """测试获取报告列表成功"""
        response = await async_client.get("/api/v1/reports/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_reports_with_filters(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试使用过滤器获取报告"""
        params = {
            "status": "completed",
            "limit": 10,
            "skip": 0,
            "search": "test"
        }
        
        response = await async_client.get(
            "/api/v1/reports/",
            params=params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_generate_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_template: Template,
        sample_data_source: DataSource,
        sample_task: Task
    ):
        """测试生成报告成功"""
        report_data = {
            "template_id": str(sample_template.id),
            "data_source_id": str(sample_data_source.id),
            "name": "测试报告",
            "description": "测试描述"
        }
        
        with patch('app.api.endpoints.reports.generate_report_task') as mock_task:
            response = await async_client.post(
                "/api/v1/reports/generate",
                json=report_data
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert "task_id" in data["data"]

    @pytest.mark.asyncio
    async def test_generate_report_invalid_template(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试使用无效模板ID生成报告"""
        report_data = {
            "template_id": "invalid-uuid",
            "data_source_id": "00000000-0000-0000-0000-000000000001"
        }
        
        response = await async_client.post(
            "/api/v1/reports/generate",
            json=report_data
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_intelligent_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_template: Template,
        sample_data_source: DataSource
    ):
        """测试生成智能报告成功"""
        report_data = {
            "template_id": str(sample_template.id),
            "data_source_id": str(sample_data_source.id),
            "optimization_level": "high_performance",
            "enable_intelligent_etl": True,
            "batch_size": 5000,
            "name": "智能测试报告"
        }
        
        with patch('app.api.endpoints.reports.generate_agent_based_intelligent_report_task') as mock_task:
            response = await async_client.post(
                "/api/v1/reports/generate/intelligent",
                json=report_data
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["optimization_level"] == "high_performance"
        assert data["data"]["agent_pipeline"] == "enabled"

    @pytest.mark.asyncio
    async def test_get_specific_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_report: ReportHistory
    ):
        """测试获取特定报告成功"""
        response = await async_client.get(f"/api/v1/reports/{sample_report.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == sample_report.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_report(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取不存在的报告"""
        response = await async_client.get("/api/v1/reports/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "不存在或无权限访问" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_report: ReportHistory
    ):
        """测试删除报告成功"""
        response = await async_client.delete(f"/api/v1/reports/{sample_report.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["report_id"] == sample_report.id

    @pytest.mark.asyncio
    async def test_batch_delete_reports_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_report: ReportHistory
    ):
        """测试批量删除报告成功"""
        delete_data = {
            "report_ids": [sample_report.id]
        }
        
        response = await async_client.delete(
            "/api/v1/reports/batch",
            json=delete_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_delete_reports_empty_list(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试批量删除空列表"""
        delete_data = {
            "report_ids": []
        }
        
        response = await async_client.delete(
            "/api/v1/reports/batch",
            json=delete_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "请提供要删除的报告ID列表" in data["detail"]

    @pytest.mark.asyncio
    async def test_regenerate_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_report: ReportHistory
    ):
        """测试重新生成报告成功"""
        with patch('app.api.endpoints.reports.regenerate_report_task') as mock_task:
            response = await async_client.post(f"/api/v1/reports/{sample_report.id}/regenerate")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "regenerating"

    @pytest.mark.asyncio
    async def test_get_report_content_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取已完成报告内容"""
        # 创建一个已完成的报告mock
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            mock_report = MagicMock()
            mock_report.id = 1
            mock_report.status = "completed"
            mock_report.result = "测试报告内容"
            mock_report.generated_at.isoformat.return_value = "2024-01-01T00:00:00"
            
            mock_query = mock_session.query.return_value
            mock_query.join.return_value.filter.return_value.first.return_value = mock_report
            
            response = await async_client.get("/api/v1/reports/1/content")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "测试报告内容"

    @pytest.mark.asyncio
    async def test_get_report_content_not_completed(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取未完成报告内容"""
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            mock_report = MagicMock()
            mock_report.status = "pending"
            
            mock_query = mock_session.query.return_value
            mock_query.join.return_value.filter.return_value.first.return_value = mock_report
            
            response = await async_client.get("/api/v1/reports/1/content")
            
        assert response.status_code == 400
        data = response.json()
        assert "尚未完成生成" in data["detail"]

    @pytest.mark.asyncio
    async def test_download_report_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试下载报告成功"""
        # 创建临时文件用于测试
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            tmp_file.write(b'test report content')
            tmp_path = tmp_file.name
        
        try:
            with patch('app.db.session.get_db') as mock_db:
                mock_session = MagicMock()
                mock_db.return_value = mock_session
                
                mock_report = MagicMock()
                mock_report.id = 1
                mock_report.status = "completed"
                mock_report.file_path = tmp_path
                mock_report.task.name = "测试任务"
                mock_report.generated_at.strftime.return_value = "20240101_120000"
                
                mock_query = mock_session.query.return_value
                mock_query.join.return_value.filter.return_value.first.return_value = mock_report
                
                response = await async_client.get("/api/v1/reports/1/download")
                
            assert response.status_code == 200
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_download_report_not_completed(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试下载未完成报告"""
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            mock_report = MagicMock()
            mock_report.status = "pending"
            
            mock_query = mock_session.query.return_value
            mock_query.join.return_value.filter.return_value.first.return_value = mock_report
            
            response = await async_client.get("/api/v1/reports/1/download")
            
        assert response.status_code == 400
        data = response.json()
        assert "尚未生成完成" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_report_info_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取报告信息成功"""
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            mock_report = MagicMock()
            mock_report.id = 1
            mock_report.task_id = 1
            mock_report.status = "completed"
            mock_report.file_path = None
            mock_report.error_message = None
            mock_report.processing_metadata = {"test": "data"}
            mock_report.generated_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_report.task.name = "测试任务"
            
            mock_query = mock_session.query.return_value
            mock_query.join.return_value.filter.return_value.first.return_value = mock_report
            
            response = await async_client.get("/api/v1/reports/1/info")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未认证访问报告API"""
        response = await async_client.get("/api/v1/reports/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_report_without_required_fields(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试缺少必需字段的报告生成"""
        invalid_data = {
            "template_id": "123"  # 缺少data_source_id
        }
        
        response = await async_client.post(
            "/api/v1/reports/generate",
            json=invalid_data
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_intelligent_report_optimization_levels(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_template: Template,
        sample_data_source: DataSource
    ):
        """测试不同优化级别的智能报告生成"""
        optimization_levels = ["standard", "high_performance", "memory_optimized"]
        
        for level in optimization_levels:
            report_data = {
                "template_id": str(sample_template.id),
                "data_source_id": str(sample_data_source.id),
                "optimization_level": level,
                "batch_size": 1000 if level == "memory_optimized" else 10000
            }
            
            with patch('app.api.endpoints.reports.generate_agent_based_intelligent_report_task') as mock_task:
                response = await async_client.post(
                    "/api/v1/reports/generate/intelligent",
                    json=report_data
                )
                
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["optimization_level"] == level

    @pytest.mark.asyncio
    async def test_report_pagination(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试报告列表分页"""
        params = {
            "skip": 10,
            "limit": 5
        }
        
        response = await async_client.get(
            "/api/v1/reports/",
            params=params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["page"] == 3  # (skip / limit) + 1
        assert data["data"]["size"] == 5

    @pytest.mark.asyncio
    async def test_report_error_handling(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试报告API错误处理"""
        # 测试数据库错误
        with patch('app.db.session.get_db') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            response = await async_client.get("/api/v1/reports/")
            
        # API应该有适当的错误处理
        assert response.status_code in [500, 503]