import pytest

def test_create_data_source(client, auth_headers):
    data = {
        "name": "API测试数据源",
        "source_type": "sql",
        "connection_string": "sqlite:///test.db",
        "is_active": True
    }
    resp = client.post("/api/v2/data-sources/", json=data, headers=auth_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_list_data_sources(client, auth_headers):
    resp = client.get("/api/v2/data-sources/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list) 