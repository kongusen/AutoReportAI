"""
任务管理API端点测试
"""
import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.user import User
from app.models.template import Template
from app.models.data_source import DataSource


class TestTasksAPI:
    """任务管理API测试类"""
    
    @pytest.mark.asyncio
    async def test_submit_ai_analysis_task_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_template: Template,
        sample_data_source: DataSource
    ):
        """测试提交AI分析任务成功"""
        task_data = {
            "template_id": sample_template.id,
            "data_source_id": sample_data_source.id,
            "analysis_type": "basic",
            "custom_instructions": "请分析数据趋势"
        }
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.delay') as mock_task:
            mock_task.return_value.id = "test-task-id"
            
            response = await async_client.post(
                "/api/v1/tasks/ai-analysis",
                json=task_data
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "pending"
        assert "template_id" in data
        assert "data_source_id" in data

    @pytest.mark.asyncio
    async def test_submit_ai_analysis_task_invalid_template(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试使用无效模板ID提交任务"""
        task_data = {
            "template_id": 99999,
            "data_source_id": 1,
            "analysis_type": "basic"
        }
        
        response = await async_client.post(
            "/api/v1/tasks/ai-analysis",
            json=task_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_task_status_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取任务状态成功"""
        task_id = "test-task-id"
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.AsyncResult') as mock_result:
            mock_result.return_value.state = "SUCCESS"
            mock_result.return_value.result = {
                "status": "completed",
                "data": {"analysis": "test result"}
            }
            mock_result.return_value.info = None
            
            response = await async_client.get(f"/api/v1/tasks/{task_id}/status")
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_get_task_result_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取任务结果成功"""
        task_id = "test-task-id"
        expected_result = {
            "analysis": "test result",
            "charts": [],
            "insights": []
        }
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.AsyncResult') as mock_result:
            mock_result.return_value.state = "SUCCESS"
            mock_result.return_value.result = expected_result
            
            response = await async_client.get(f"/api/v1/tasks/{task_id}/result")
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "SUCCESS"
        assert data["result"] == expected_result

    @pytest.mark.asyncio
    async def test_get_task_result_pending(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取未完成任务结果"""
        task_id = "pending-task-id"
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.AsyncResult') as mock_result:
            mock_result.return_value.state = "PENDING"
            mock_result.return_value.result = None
            
            response = await async_client.get(f"/api/v1/tasks/{task_id}/result")
            
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_cancel_task_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试取消任务成功"""
        task_id = "test-task-id"
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.AsyncResult') as mock_result:
            mock_result.return_value.revoke.return_value = True
            
            response = await async_client.post(f"/api/v1/tasks/{task_id}/cancel")
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_user_tasks(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取用户任务列表"""
        with patch('app.crud.crud_task.crud_task.get_user_tasks') as mock_get_tasks:
            mock_tasks = [
                {
                    "id": 1,
                    "task_id": "task-1",
                    "status": "completed",
                    "created_at": "2024-01-01T00:00:00"
                },
                {
                    "id": 2,
                    "task_id": "task-2", 
                    "status": "pending",
                    "created_at": "2024-01-01T01:00:00"
                }
            ]
            mock_get_tasks.return_value = mock_tasks
            
            response = await async_client.get("/api/v1/tasks/")
            
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["task_id"] == "task-1"
        assert data[1]["task_id"] == "task-2"

    @pytest.mark.asyncio
    async def test_submit_batch_analysis_task(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_data_source: DataSource
    ):
        """测试提交批量分析任务"""
        batch_data = {
            "data_source_id": sample_data_source.id,
            "queries": [
                "SELECT * FROM users WHERE created_at > '2024-01-01'",
                "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
            ],
            "analysis_type": "batch"
        }
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.batch_analysis_task.delay') as mock_task:
            mock_task.return_value.id = "batch-task-id"
            
            response = await async_client.post(
                "/api/v1/tasks/batch-analysis",
                json=batch_data
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "batch-task-id"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task_logs(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取任务日志"""
        task_id = "test-task-id"
        
        with patch('app.services.application.task_management.infrastructure.services.task_execution_service.TaskExecutionService.get_task_logs') as mock_get_logs:
            mock_logs = [
                {"timestamp": "2024-01-01T00:00:00", "level": "INFO", "message": "Task started"},
                {"timestamp": "2024-01-01T00:01:00", "level": "INFO", "message": "Processing data"},
                {"timestamp": "2024-01-01T00:02:00", "level": "INFO", "message": "Task completed"}
            ]
            mock_get_logs.return_value = mock_logs
            
            response = await async_client.get(f"/api/v1/tasks/{task_id}/logs")
            
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["message"] == "Task started"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未认证访问"""
        response = await async_client.get("/api/v1/tasks/")
        assert response.status_code == 401

    @pytest.mark.asyncio 
    async def test_submit_task_with_invalid_data(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试提交无效数据的任务"""
        invalid_data = {
            "template_id": "invalid",  # 应该是整数
            "data_source_id": None,   # 不能为空
        }
        
        response = await async_client.post(
            "/api/v1/tasks/ai-analysis",
            json=invalid_data
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_status(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取不存在任务的状态"""
        task_id = "nonexistent-task-id"
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.AsyncResult') as mock_result:
            mock_result.return_value.state = "PENDING"
            mock_result.return_value.result = None
            
            response = await async_client.get(f"/api/v1/tasks/{task_id}/status")
            
        assert response.status_code == 200  # Celery返回PENDING状态即使任务不存在
        data = response.json()
        assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_task_with_custom_parameters(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User,
        sample_template: Template,
        sample_data_source: DataSource
    ):
        """测试带自定义参数的任务提交"""
        task_data = {
            "template_id": sample_template.id,
            "data_source_id": sample_data_source.id,
            "analysis_type": "advanced",
            "custom_instructions": "分析销售趋势",
            "parameters": {
                "time_range": "30d",
                "metrics": ["revenue", "conversions"],
                "filters": {"status": "active"}
            }
        }
        
        with patch('app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.analyze_data_task.delay') as mock_task:
            mock_task.return_value.id = "custom-task-id"
            
            response = await async_client.post(
                "/api/v1/tasks/ai-analysis",
                json=task_data
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "custom-task-id"
        
        # 验证任务调用时传递了正确的参数
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        assert "parameters" in call_args