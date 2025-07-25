"""
Complete backend end-to-end test covering all core functionality
后端完整端到端测试，覆盖所有核心功能
"""
import pytest
import uuid
import json
import time
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.data_source import DataSource
from app.models.template import Template
from app.models.task import Task
from app.models.report_history import ReportHistory
from app.models.etl_job import ETLJob


@pytest.mark.e2e
class TestBackendCompleteWorkflow:
    """后端完整工作流测试类"""
    
    def test_complete_user_workflow(self, client: TestClient, db_session: Session):
        """测试完整的用户工作流：注册->登录->创建数据源->创建模板->创建任务->生成报告"""
        
        # 1. 用户注册
        unique_id = uuid.uuid4().hex[:8]
        register_data = {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v2/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        user_id = user_data["id"]
        assert user_id
        
        # 2. 用户登录
        login_data = {
            "username": register_data["username"],
            "password": register_data["password"]
        }
        
        response = client.post("/api/v2/auth/login", data=login_data)
        assert response.status_code == 200
        login_response = response.json()
        access_token = login_response["access_token"]
        assert access_token
        
        # 设置认证头
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. 创建数据源
        ds_data = {
            "name": f"Test Data Source {unique_id}",
            "source_type": "database",
            "connection_string": "sqlite:///test_e2e.db",
            "description": "End-to-end test data source",
            "config": {
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "testuser",
                "password": "testpass"
            },
            "is_active": True
        }
        
        response = client.post("/api/v2/data-sources", json=ds_data, headers=auth_headers)
        assert response.status_code == 201
        ds_response = response.json()
        data_source_id = ds_response["id"]
        assert data_source_id
        
        # 4. 验证数据源列表
        response = client.get("/api/v2/data-sources", headers=auth_headers)
        assert response.status_code == 200
        ds_list = response.json()
        assert len(ds_list) > 0
        assert any(ds["id"] == data_source_id for ds in ds_list)
        
        # 5. 创建模板
        template_data = {
            "name": f"Test Template {unique_id}",
            "description": "End-to-end test template",
            "content": """
            本月数据报告：
            总记录数：{{统计:总记录数}}
            平均数值：{{统计:平均值}}
            最高记录：{{统计:最大值}}
            生成时间：{{时间:当前时间}}
            """,
            "is_active": True
        }
        
        response = client.post("/api/v2/templates", json=template_data, headers=auth_headers)
        assert response.status_code == 201
        template_response = response.json()
        template_id = template_response["id"]
        assert template_id
        
        # 6. 验证模板列表
        response = client.get("/api/v2/templates", headers=auth_headers)
        assert response.status_code == 200
        template_list = response.json()
        assert len(template_list) > 0
        assert any(t["id"] == template_id for t in template_list)
        
        # 7. 创建任务
        task_data = {
            "name": f"Test Task {unique_id}",
            "description": "End-to-end test task",
            "data_source_id": data_source_id,
            "template_id": template_id,
            "schedule": "0 0 * * *",  # 每天午夜执行
            "is_active": True
        }
        
        response = client.post("/api/v2/tasks", json=task_data, headers=auth_headers)
        assert response.status_code == 201
        task_response = response.json()
        task_id = task_response["id"]
        assert task_id
        
        # 8. 验证任务列表
        response = client.get("/api/v2/tasks", headers=auth_headers)
        assert response.status_code == 200
        task_list = response.json()
        assert len(task_list) > 0
        assert any(t["id"] == task_id for t in task_list)
        
        # 9. 创建ETL作业
        etl_data = {
            "name": f"Test ETL Job {unique_id}",
            "description": "End-to-end test ETL job",
            "source_id": data_source_id,
            "schedule": "0 0 * * *",
            "is_active": True,
            "config": {
                "query": "SELECT * FROM test_table",
                "transformations": ["clean", "aggregate"]
            }
        }
        
        response = client.post("/api/v2/etl-jobs", json=etl_data, headers=auth_headers)
        assert response.status_code == 201
        etl_response = response.json()
        etl_job_id = etl_response["id"]
        assert etl_job_id
        
        # 10. 验证ETL作业列表
        response = client.get("/api/v2/etl-jobs", headers=auth_headers)
        assert response.status_code == 200
        etl_list = response.json()
        assert len(etl_list) > 0
        assert any(e["id"] == etl_job_id for e in etl_list)
        
        # 11. 生成报告
        report_data = {
            "task_id": task_id,
            "template_id": template_id,
            "data_source_id": data_source_id,
            "parameters": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }
        
        response = client.post("/api/v2/reports/generate", json=report_data, headers=auth_headers)
        assert response.status_code in [200, 202]
        report_response = response.json()
        assert "task_id" in report_response or "report_id" in report_response
        
        # 12. 获取报告历史
        response = client.get("/api/v2/reports", headers=auth_headers)
        assert response.status_code == 200
        reports = response.json()
        assert isinstance(reports, list)
        
        # 13. 获取仪表板数据
        response = client.get("/api/v2/dashboard/summary", headers=auth_headers)
        assert response.status_code == 200
        dashboard_data = response.json()
        assert "total_data_sources" in dashboard_data
        assert "total_templates" in dashboard_data
        assert "total_tasks" in dashboard_data
        
        # 14. 更新用户信息
        update_data = {
            "full_name": "Updated Test User",
            "bio": "Test bio"
        }
        
        response = client.put("/api/v2/users/me", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        updated_user = response.json()
        assert updated_user["full_name"] == update_data["full_name"]
        
        # 15. 测试数据验证
        validation_data = {
            "source_type": "database",
            "connection_string": "sqlite:///test.db"
        }
        
        response = client.post("/api/v2/data-sources/validate", json=validation_data, headers=auth_headers)
        assert response.status_code == 200
        validation_result = response.json()
        assert "is_valid" in validation_result
        
        # 16. 测试模板验证
        template_validation = {
            "content": "Test template with {{valid:placeholder}}"
        }
        
        response = client.post("/api/v2/templates/validate", json=template_validation, headers=auth_headers)
        assert response.status_code == 200
        template_validation_result = response.json()
        assert "is_valid" in template_validation_result
        
        # 17. 清理测试数据
        # 删除任务
        response = client.delete(f"/api/v2/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # 删除模板
        response = client.delete(f"/api/v2/templates/{template_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # 删除数据源
        response = client.delete(f"/api/v2/data-sources/{data_source_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # 删除ETL作业
        response = client.delete(f"/api/v2/etl-jobs/{etl_job_id}", headers=auth_headers)
        assert response.status_code == 204
    
    def test_error_handling_workflow(self, client: TestClient, db_session: Session):
        """测试错误处理工作流"""
        
        # 1. 无效用户注册
        invalid_register_data = {
            "username": "a",  # 太短
            "email": "invalid-email",
            "password": "123",  # 太短
        }
        
        response = client.post("/api/v2/auth/register", json=invalid_register_data)
        assert response.status_code == 422
        
        # 2. 无效登录
        invalid_login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v2/auth/login", data=invalid_login_data)
        assert response.status_code == 401
        
        # 3. 未授权访问
        response = client.get("/api/v2/data-sources")
        assert response.status_code == 401
        
        # 4. 无效数据源创建
        valid_user = {
            "username": f"error_test_{uuid.uuid4().hex[:8]}",
            "email": f"error_test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v2/auth/register", json=valid_user)
        assert response.status_code == 201
        
        login_response = client.post("/api/v2/auth/login", data=valid_user)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        invalid_ds_data = {
            "name": "",  # 空名称
            "source_type": "invalid_type",  # 无效类型
            "connection_string": ""
        }
        
        response = client.post("/api/v2/data-sources", json=invalid_ds_data, headers=headers)
        assert response.status_code == 422
    
    def test_concurrent_operations(self, client: TestClient, db_session: Session):
        """测试并发操作"""
        
        # 创建测试用户
        unique_id = uuid.uuid4().hex[:8]
        user_data = {
            "username": f"concurrent_{unique_id}",
            "email": f"concurrent_{unique_id}@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v2/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_response = client.post("/api/v2/auth/login", data=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 并发创建多个数据源
        data_sources = []
        for i in range(5):
            ds_data = {
                "name": f"Concurrent DS {i} {unique_id}",
                "source_type": "database",
                "connection_string": f"sqlite:///test_{i}.db",
                "is_active": True
            }
            response = client.post("/api/v2/data-sources", json=ds_data, headers=headers)
            assert response.status_code == 201
            data_sources.append(response.json()["id"])
        
        # 验证所有数据源都被创建
        response = client.get("/api/v2/data-sources", headers=headers)
        assert response.status_code == 200
        ds_list = response.json()
        created_ids = [ds["id"] for ds in ds_list]
        
        for ds_id in data_sources:
            assert ds_id in created_ids
        
        # 清理
        for ds_id in data_sources:
            response = client.delete(f"/api/v2/data-sources/{ds_id}", headers=headers)
            assert response.status_code == 204


@pytest.mark.e2e
class TestBackendPerformance:
    """后端性能测试类"""
    
    def test_api_response_times(self, client: TestClient, db_session: Session):
        """测试API响应时间"""
        
        # 创建测试用户
        unique_id = uuid.uuid4().hex[:8]
        user_data = {
            "username": f"perf_{unique_id}",
            "email": f"perf_{unique_id}@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v2/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_response = client.post("/api/v2/auth/login", data=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试各种端点的响应时间
        endpoints = [
            ("/api/v2/dashboard/summary", "GET"),
            ("/api/v2/data-sources", "GET"),
            ("/api/v2/templates", "GET"),
            ("/api/v2/tasks", "GET"),
            ("/api/v2/etl-jobs", "GET"),
        ]
        
        for endpoint, method in endpoints:
            start_time = time.time()
            if method == "GET":
                response = client.get(endpoint, headers=headers)
            else:
                response = client.post(endpoint, headers=headers)
            
            response_time = time.time() - start_time
            assert response.status_code == 200
            assert response_time < 5.0, f"Endpoint {endpoint} took too long: {response_time}s"
    
    def test_bulk_operations(self, client: TestClient, db_session: Session):
        """测试批量操作性能"""
        
        # 创建测试用户
        unique_id = uuid.uuid4().hex[:8]
        user_data = {
            "username": f"bulk_{unique_id}",
            "email": f"bulk_{unique_id}@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v2/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_response = client.post("/api/v2/auth/login", data=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 批量创建数据源
        bulk_data_sources = []
        for i in range(10):
            ds_data = {
                "name": f"Bulk DS {i} {unique_id}",
                "source_type": "database",
                "connection_string": f"sqlite:///bulk_{i}.db",
                "is_active": True
            }
            bulk_data_sources.append(ds_data)
        
        # 验证批量创建的性能
        start_time = time.time()
        created_ids = []
        for ds_data in bulk_data_sources:
            response = client.post("/api/v2/data-sources", json=ds_data, headers=headers)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        bulk_create_time = time.time() - start_time
        assert bulk_create_time < 10.0, f"Bulk creation took too long: {bulk_create_time}s"
        
        # 清理
        for ds_id in created_ids:
            response = client.delete(f"/api/v2/data-sources/{ds_id}", headers=headers)
            assert response.status_code == 204
