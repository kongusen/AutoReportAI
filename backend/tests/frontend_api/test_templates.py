import pytest

def test_create_template(client, auth_headers):
    data = {
        "name": "API测试模板",
        "description": "自动化测试模板",
        "content": "本月数据报告：总记录数：{{统计:总记录数}}",
        "is_active": True
    }
    resp = client.post("/api/v2/templates/", json=data, headers=auth_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_list_templates(client, auth_headers):
    resp = client.get("/api/v2/templates/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list) 