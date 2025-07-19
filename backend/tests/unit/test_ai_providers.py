import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, schemas

# Fixtures will be imported from conftest.py automatically
from app.core.config import settings


def create_superuser_token(
    client: TestClient, db_session: Session, username: str
) -> str:
    """Helper function to create a superuser and return access token"""
    # Create superuser
    superuser_data = {
        "username": username,
        "password": "password123",
        "is_superuser": True,
    }
    superuser = crud.user.create(
        db_session, obj_in=schemas.UserCreate(**superuser_data)
    )

    # Login to get access token
    login_data = {"username": username, "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_ai_provider(client: TestClient, db_session: Session):
    """Test creating a new AI provider"""
    # First create a superuser
    superuser_data = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "password123",
        "is_superuser": True,
    }
    superuser = crud.user.create(
        db_session, obj_in=schemas.UserCreate(**superuser_data)
    )

    # Login to get access token
    login_data = {"username": "admin", "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Test creating AI provider
    provider_data = {
        "provider_name": "OpenAI",
        "provider_type": "openai",
        "api_key": "sk-test-key-123",
        "api_base_url": "https://api.openai.com/v1",
        "default_model_name": "gpt-4",
        "is_active": 1,
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)
    assert response.status_code == 200

    created_provider = response.json()
    assert created_provider["provider_name"] == "OpenAI"
    assert created_provider["provider_type"] == "openai"
    assert created_provider["default_model_name"] == "gpt-4"
    assert created_provider["is_active"] == 1


def test_get_ai_providers(client: TestClient, db_session: Session):
    """Test retrieving AI providers"""
    # Create superuser and login
    superuser_data = {
        "username": "admin2",
        "email": "admin2@example.com",
        "password": "password123",
        "is_superuser": True,
    }
    superuser = crud.user.create(
        db_session, obj_in=schemas.UserCreate(**superuser_data)
    )

    login_data = {"username": "admin2", "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create test provider
    provider_data = {
        "provider_name": "Claude",
        "provider_type": "openai",
        "api_key": "sk-test-claude-key",
        "api_base_url": "https://api.anthropic.com",
        "default_model_name": "claude-3-sonnet",
        "is_active": 1,
    }

    client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)

    # Test getting providers
    response = client.get("/api/v1/ai-providers/", headers=headers)
    assert response.status_code == 200

    providers = response.json()
    assert len(providers) >= 1
    assert any(p["provider_name"] == "Claude" for p in providers)


def test_get_active_ai_provider(client: TestClient, db_session: Session):
    """Test getting the active AI provider"""
    # Create superuser and login
    superuser_data = {
        "username": "admin3",
        "email": "admin3@example.com",
        "password": "password123",
        "is_superuser": True,
    }
    superuser = crud.user.create(
        db_session, obj_in=schemas.UserCreate(**superuser_data)
    )

    login_data = {"username": "admin3", "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create active provider
    provider_data = {
        "provider_name": "ActiveAI",
        "provider_type": "openai",
        "api_key": "sk-active-key",
        "api_base_url": "https://api.activeai.com",
        "default_model_name": "active-model",
        "is_active": 1,
    }

    client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)

    # Test getting active provider
    response = client.get("/api/v1/ai-providers/active")
    assert response.status_code == 200

    active_provider = response.json()
    assert active_provider["provider_name"] == "ActiveAI"
    assert active_provider["is_active"] == 1


def test_create_ai_provider_duplicate_name(client: TestClient, db_session: Session):
    """Test creating AI provider with duplicate name should fail"""
    # Create superuser and login
    superuser_data = {
        "username": "admin4",
        "email": "admin4@example.com",
        "password": "password123",
        "is_superuser": True,
    }
    superuser = crud.user.create(
        db_session, obj_in=schemas.UserCreate(**superuser_data)
    )

    login_data = {"username": "admin4", "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create first provider
    provider_data = {
        "provider_name": "DuplicateTest",
        "provider_type": "openai",
        "api_key": "sk-test-key-1",
        "api_base_url": "https://api.test.com",
        "default_model_name": "test-model",
        "is_active": 1,
    }

    response = client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)
    assert response.status_code == 200

    # Try to create duplicate
    response = client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_ai_provider_unauthorized(client: TestClient, db_session: Session):
    """Test creating AI provider without superuser permissions should fail"""
    # Create regular user
    user_data = {
        "username": "regular_user",
        "email": "regular@example.com",
        "password": "password123",
        "is_superuser": False,
    }
    user = crud.user.create(db_session, obj_in=schemas.UserCreate(**user_data))

    login_data = {"username": "regular_user", "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to create provider as regular user
    provider_data = {
        "provider_name": "UnauthorizedTest",
        "provider_type": "openai",
        "api_key": "sk-MQWe6wOtgq75cQpK2gGwV9Ninqc5jrxBBWDETRCI8h7PzTkb",
        "api_base_url": "https://xiaoai.plus/v1",
        "default_model_name": "gpt-4o-mini",
        "is_active": 1,
    }

    response = client.post("/api/v1/ai-providers/", json=provider_data, headers=headers)
    assert response.status_code == 403


def test_test_ai_provider_connection_success(client: TestClient, db_session: Session):
    """Test AI provider connection test endpoint - success case"""
    # Create superuser and login
    token = create_superuser_token(client, db_session, "admin_connection_test")
    headers = {"Authorization": f"Bearer {token}"}

    # Create test provider
    provider_data = {
        "provider_name": "TestConnection",
        "provider_type": "openai",
        "api_key": "sk-test-key-for-connection",
        "api_base_url": "https://api.openai.com/v1",
        "default_model_name": "gpt-3.5-turbo",
        "is_active": 1,
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider_data, headers=headers
    )
    assert create_response.status_code == 200
    provider_id = create_response.json()["id"]

    # Test connection (this will fail in test environment, but we test the endpoint)
    response = client.post(
        f"{settings.API_V1_STR}/ai-providers/{provider_id}/test", headers=headers
    )
    # In test environment, this will likely fail due to invalid API key
    # but we test that the endpoint exists and returns proper error
    assert response.status_code in [200, 400]


def test_activate_ai_provider(client: TestClient, db_session: Session):
    """Test activating an AI provider"""
    token = create_superuser_token(client, db_session, "admin_activate")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two providers
    provider1_data = {
        "provider_name": "Provider1",
        "provider_type": "openai",
        "api_key": "sk-test-key-1",
        "default_model_name": "gpt-3.5-turbo",
        "is_active": 1,
    }

    provider2_data = {
        "provider_name": "Provider2",
        "provider_type": "openai",
        "api_key": "sk-test-key-2",
        "default_model_name": "gpt-4",
        "is_active": 0,
    }

    # Create providers
    response1 = client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider1_data, headers=headers
    )
    response2 = client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider2_data, headers=headers
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    provider1_id = response1.json()["id"]
    provider2_id = response2.json()["id"]

    # Activate provider2
    activate_response = client.post(
        f"{settings.API_V1_STR}/ai-providers/{provider2_id}/activate", headers=headers
    )

    assert activate_response.status_code == 200
    activated_provider = activate_response.json()
    assert activated_provider["is_active"] == 1

    # Check that provider1 is now deactivated
    get_response = client.get(
        f"{settings.API_V1_STR}/ai-providers/{provider1_id}", headers=headers
    )
    assert get_response.status_code == 200
    # Note: We need to add a get single provider endpoint for this test to work properly


def test_deactivate_ai_provider(client: TestClient, db_session: Session):
    """Test deactivating an AI provider"""
    token = create_superuser_token(client, db_session, "admin_deactivate")
    headers = {"Authorization": f"Bearer {token}"}

    # Create active provider
    provider_data = {
        "provider_name": "ActiveProvider",
        "provider_type": "openai",
        "api_key": "sk-test-key-active",
        "default_model_name": "gpt-3.5-turbo",
        "is_active": 1,
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider_data, headers=headers
    )
    assert create_response.status_code == 200
    provider_id = create_response.json()["id"]

    # Deactivate provider
    deactivate_response = client.post(
        f"{settings.API_V1_STR}/ai-providers/{provider_id}/deactivate", headers=headers
    )

    assert deactivate_response.status_code == 200
    deactivated_provider = deactivate_response.json()
    assert deactivated_provider["is_active"] == 0


def test_get_ai_provider_models(client: TestClient, db_session: Session):
    """Test getting available models from an AI provider"""
    token = create_superuser_token(client, db_session, "admin_models")
    headers = {"Authorization": f"Bearer {token}"}

    # Create provider
    provider_data = {
        "provider_name": "ModelProvider",
        "provider_type": "openai",
        "api_key": "sk-test-key-models",
        "default_model_name": "gpt-3.5-turbo",
        "is_active": 1,
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider_data, headers=headers
    )
    assert create_response.status_code == 200
    provider_id = create_response.json()["id"]

    # Get models (this will fail in test environment, but we test the endpoint)
    response = client.get(
        f"{settings.API_V1_STR}/ai-providers/{provider_id}/models", headers=headers
    )
    # In test environment, this will likely return default models
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        models = response.json()
        assert isinstance(models, list)


def test_ai_providers_health_check(client: TestClient, db_session: Session):
    """Test AI providers health check endpoint"""
    token = create_superuser_token(client, db_session, "admin_health")
    headers = {"Authorization": f"Bearer {token}"}

    # Test health check with no providers
    response = client.get(f"{settings.API_V1_STR}/ai-providers/health", headers=headers)
    assert response.status_code == 200
    assert "No AI providers configured" in response.json()["msg"]

    # Create a provider
    provider_data = {
        "provider_name": "HealthProvider",
        "provider_type": "openai",
        "api_key": "sk-test-key-health",
        "default_model_name": "gpt-3.5-turbo",
        "is_active": 1,
    }

    client.post(
        f"{settings.API_V1_STR}/ai-providers/", json=provider_data, headers=headers
    )

    # Test health check with active provider
    response = client.get(f"{settings.API_V1_STR}/ai-providers/health", headers=headers)
    assert response.status_code == 200
    assert "HealthProvider" in response.json()["msg"]
