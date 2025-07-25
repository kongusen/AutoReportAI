import pytest

def test_register(client):
    data = {
        "username": "testuser_api",
        "email": "testuser_api@example.com",
        "password": "TestPass123!",
        "full_name": "Test User API"
    }
    resp = client.post("/api/v2/auth/register", json=data)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_login(client):
    data = {"username": "testuser_api", "password": "TestPass123!"}
    resp = client.post("/api/v2/auth/login", data=data)
    assert resp.status_code == 200
    assert "access_token" in resp.json()

def test_get_user_info(client, auth_headers):
    resp = client.get("/api/v2/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json().get("success") 