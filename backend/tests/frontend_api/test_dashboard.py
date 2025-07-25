import pytest

def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/v2/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert "data_sources" in data
    assert "templates" in data
    assert "tasks" in data

def test_dashboard_recent_activity(client, auth_headers):
    resp = client.get("/api/v2/dashboard/recent-activity", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert "recent_reports" in data
    assert "recent_tasks" in data
    assert "recent_data_sources" in data 