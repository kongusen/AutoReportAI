import pytest
import uuid

def test_user_registration_and_login(client):
    """用户故事：注册与登录"""
    unique_id = uuid.uuid4().hex[:8]
    reg_data = {
        "username": f"e2euser_{unique_id}",
        "email": f"e2euser_{unique_id}@example.com",
        "password": "TestPass123!",
        "full_name": "E2E User"
    }
    resp = client.post("/api/v2/auth/register", json=reg_data)
    assert resp.status_code == 201
    login_data = {"username": reg_data["username"], "password": reg_data["password"]}
    resp = client.post("/api/v2/auth/login", data=login_data)
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v2/auth/me", headers=headers)
    assert resp.status_code == 200

def test_data_source_lifecycle(client, auth_headers):
    """用户故事：数据源管理"""
    ds_data = {
        "name": "E2E测试数据源",
        "source_type": "sql",
        "connection_string": "sqlite:///test_e2e.db",
        "is_active": True
    }
    resp = client.post("/api/v2/data-sources/", json=ds_data, headers=auth_headers)
    assert resp.status_code == 201
    ds_id = resp.json()["id"]
    resp = client.get("/api/v2/data-sources/", headers=auth_headers)
    assert any(ds["id"] == ds_id for ds in resp.json().get("data", {}).get("items", []))
    resp = client.post(f"/api/v2/data-sources/{ds_id}/test", headers=auth_headers)
    assert resp.status_code == 200

def test_report_generation_flow(client, auth_headers):
    """用户故事：模板-任务-报告全链路"""
    # 先创建数据源
    ds_data = {
        "name": "E2E测试数据源2",
        "source_type": "sql",
        "connection_string": "sqlite:///test_e2e2.db",
        "is_active": True
    }
    ds_resp = client.post("/api/v2/data-sources/", json=ds_data, headers=auth_headers)
    assert ds_resp.status_code == 201
    ds_id = ds_resp.json()["id"]
    # 创建模板
    tpl_data = {
        "name": "E2E测试模板",
        "description": "自动化E2E测试模板",
        "content": "本月数据报告：总记录数：{{统计:总记录数}}",
        "is_active": True
    }
    resp = client.post("/api/v2/templates/", json=tpl_data, headers=auth_headers)
    assert resp.status_code == 201
    tpl_id = resp.json()["id"]
    # 查询数据源
    ds_resp = client.get("/api/v2/data-sources/", headers=auth_headers)
    ds_items = ds_resp.json().get("data", {}).get("items", [])
    assert ds_items
    ds_id = ds_items[0]["id"]
    # 创建任务
    task_data = {
        "name": "E2E测试任务",
        "description": "自动化E2E测试任务",
        "data_source_id": ds_id,
        "template_id": tpl_id,
        "is_active": True
    }
    resp = client.post("/api/v2/tasks/", json=task_data, headers=auth_headers)
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    params = {"template_id": tpl_id, "data_source_id": ds_id}
    resp = client.post("/api/v2/reports/generate", params=params, headers=auth_headers)
    assert resp.status_code in [200, 202]
    # 可继续扩展报告下载、历史等

def test_dashboard_stats_and_activity(client, auth_headers):
    """用户故事：仪表板统计与最近活动"""
    resp = client.get("/api/v2/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    resp = client.get("/api/v2/dashboard/recent-activity", headers=auth_headers)
    assert resp.status_code == 200 