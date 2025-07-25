import pytest

def test_generate_report(client, auth_headers, template_id, data_source_id):
    params = {
        "template_id": template_id,
        "data_source_id": data_source_id
    }
    resp = client.post("/api/v2/reports/generate", params=params, headers=auth_headers)
    assert resp.status_code in [200, 202]

def test_list_reports(client, auth_headers):
    resp = client.get("/api/v2/reports/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list) 