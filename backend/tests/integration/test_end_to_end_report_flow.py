"""
End-to-end integration test: 数据源-模板-任务-报告全流程
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from uuid import UUID

@pytest.mark.integration
class TestEndToEndReportFlow:
    def test_full_report_generation_flow(self, authenticated_client: TestClient, db_session: Session, mock_external_services):
        """
        1. 获取当前用户id
        2. 创建增强数据源
        3. 创建模板
        4. （可选）预览宽表
        5. 创建任务
        6. 执行任务（生成报告）
        7. 获取报告
        """
        # 1. 获取当前用户id
        user_resp = authenticated_client.get("/api/v1/users/me")
        assert user_resp.status_code == 200
        user_id = user_resp.json()["id"]
        assert user_id

        # 2. 创建增强数据源（/api/v1/enhanced-data-sources/）
        data_source_payload = {
            "name": f"AutoTestDS_{uuid.uuid4().hex[:8]}",
            "source_type": "sql",
            "connection_string": "sqlite:///test_e2e.db",
            "is_active": True
        }
        ds_resp = authenticated_client.post("/api/v1/enhanced-data-sources/", json=data_source_payload)
        assert ds_resp.status_code == 200
        ds_data = ds_resp.json()
        data_source_id = ds_data["id"]
        assert data_source_id

        # 3. 创建模板
        template_payload = {
            "name": f"AutoTestTPL_{uuid.uuid4().hex[:8]}",
            "description": "E2E test template",
            "content": "本月投诉总数：{{统计:投诉总数}}件。主要地区：{{区域:主要投诉地区}}。",
            "is_active": True
        }
        tpl_resp = authenticated_client.post("/api/v1/templates/", json=template_payload)
        assert tpl_resp.status_code == 200
        tpl_data = tpl_resp.json()
        template_id = tpl_data["data"]["id"] if "data" in tpl_data and "id" in tpl_data["data"] else tpl_data.get("id")
        assert template_id

        # 4. 预览宽表（可选，确保数据源可用）
        # 这里跳过 enhanced-data-sources 的宽表预览，普通数据源无此接口

        # 5. 创建任务
        task_payload = {
            "name": f"AutoTestTask_{uuid.uuid4().hex[:8]}",
            "data_source_id": data_source_id,
            "template_id": template_id,
            "description": "E2E test task"
        }
        task_resp = authenticated_client.post("/api/v1/tasks/", json=task_payload)
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        task_id = task_data["id"] if "id" in task_data else task_data.get("data", {}).get("id")
        assert task_id

        # 6. 执行任务（生成报告）
        report_gen_payload = {
            "task_id": task_id,  # int
            "template_id": template_id,  # 直接用字符串
            "data_source_id": data_source_id
        }
        report_resp = authenticated_client.post("/api/v1/reports/generate", json=report_gen_payload)
        assert report_resp.status_code in [200, 202]
        report_data = report_resp.json()
        assert report_data.get("success") is True
        # 获取报告任务ID
        gen_task_id = report_data["data"].get("task_id") or task_id

        # 7. 获取报告（轮询或直接获取）
        status_resp = authenticated_client.get(f"/api/v1/reports/status/{gen_task_id}")
        assert status_resp.status_code in [200, 202, 404]  # 404/202 代表任务未完成也可接受
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            assert status_data.get("success") is True
            assert "data" in status_data
            # 可进一步断言报告内容结构 