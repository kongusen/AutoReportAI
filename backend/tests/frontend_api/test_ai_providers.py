import pytest
import os

def test_list_ai_providers(client, auth_headers):
    resp = client.get("/api/v2/ai-providers/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("data", {}).get("items", []), list)

def test_create_ai_provider(client, auth_headers):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("未设置OPENAI_API_KEY，跳过AI Provider创建测试")
    data = {
        "provider_name": "pytest-provider",
        "provider_type": "openai",
        "api_key": api_key,
        "api_base_url": "https://api.openai.com/v1",
        "default_model_name": "gpt-4o",
        "is_active": True
    }
    resp = client.post("/api/v2/ai-providers/", json=data, headers=auth_headers)
    assert resp.status_code == 200 or resp.status_code == 400  # 已存在也可通过

def test_test_ai_provider(client, auth_headers):
    # 获取第一个provider
    resp = client.get("/api/v2/ai-providers/", headers=auth_headers)
    providers = resp.json().get("data", {}).get("items", [])
    if not providers:
        pytest.skip("无AI Provider，跳过连通性测试")
    provider_id = providers[0]["id"]
    resp = client.post(f"/api/v2/ai-providers/{provider_id}/test", headers=auth_headers)
    assert resp.status_code == 200 or resp.status_code == 400 