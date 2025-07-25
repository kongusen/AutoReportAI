import pytest

def test_create_task(client, auth_headers, data_source_id, template_id):
    data = {
        "name": "API测试任务",
        "description": "自动化测试任务",
        "data_source_id": data_source_id,
        "template_id": template_id,
        "is_active": True
    }
    resp = client.post("/api/v2/tasks/", json=data, headers=auth_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_list_tasks(client, auth_headers):
    resp = client.get("/api/v2/tasks/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list) 