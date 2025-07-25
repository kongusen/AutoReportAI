import pytest

def test_create_etl_job(client, auth_headers, data_source_id):
    data = {
        "name": "API测试ETL作业",
        "description": "自动化测试ETL作业",
        "data_source_id": data_source_id,
        "destination_table_name": "etl_table_api",
        "source_query": "SELECT * FROM test_table",
        "schedule": "0 0 * * *",
        "enabled": True
    }
    resp = client.post("/api/v2/etl-jobs/", json=data, headers=auth_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_list_etl_jobs(client, auth_headers):
    resp = client.get("/api/v2/etl-jobs/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list) 