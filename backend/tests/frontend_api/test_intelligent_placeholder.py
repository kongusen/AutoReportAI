import pytest

def test_intelligent_placeholder_match(client, auth_headers):
    data = {
        "text": "本月销售总额是多少？",
        "context": {"columns": ["销售额", "月份"]}
    }
    resp = client.post("/api/v2/intelligent-placeholder/match", json=data, headers=auth_headers)
    assert resp.status_code == 200
    assert "matches" in resp.json().get("data", {})

def test_field_matcher(client, auth_headers):
    data = {
        "fields": ["销售额", "月份"],
        "query": "请匹配销售相关字段"
    }
    resp = client.post("/api/v2/field-matcher/match", json=data, headers=auth_headers)
    assert resp.status_code == 200
    assert "matched_fields" in resp.json().get("data", {}) 