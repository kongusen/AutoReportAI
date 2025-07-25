import pytest
import uuid

@pytest.fixture
def auth_headers(client):
    unique_id = uuid.uuid4().hex[:8]
    reg_data = {
        "username": f"e2euser_{unique_id}",
        "email": f"e2euser_{unique_id}@example.com",
        "password": "TestPass123!",
        "full_name": "E2E User"
    }
    client.post("/api/v2/auth/register", json=reg_data)
    login_data = {"username": reg_data["username"], "password": reg_data["password"]}
    resp = client.post("/api/v2/auth/login", data=login_data)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"} 