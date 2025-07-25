"""
Integration test specific configuration and fixtures.

Integration tests verify that different components work together correctly,
including database operations, service integrations, and API endpoints.
"""

from typing import Any, Dict, Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.orm import Session

from app import crud, schemas
from app.models.data_source import DataSource
from app.models.etl_job import ETLJob
from app.models.template import Template
from app.models.user import User


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db_session: Session) -> User:
    """使用真实admin用户作为测试用户"""
    user = crud.user.get_by_username(db_session, username="admin")
    if user is None:
        user_data = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "password",
            "is_superuser": True,
        }
        user = crud.user.create(db_session, obj_in=schemas.UserCreate(**user_data))
    return user


@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """使用真实admin用户作为超级用户"""
    user = crud.user.get_by_username(db_session, username="admin")
    if user is None:
        user_data = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "password",
            "is_superuser": True,
        }
        user = crud.user.create(db_session, obj_in=schemas.UserCreate(**user_data))
    return user


@pytest.fixture
def test_data_source(db_session: Session, test_user: User) -> DataSource:
    """Create a test data source in the database"""
    data_source_data = {
        "name": "Integration Test Data Source",
        "description": "Data source for integration testing",
        "source_type": "database",
        "connection_string": "sqlite:///integration_test.db",
        "is_active": True,
        "user_id": test_user.id,
    }
    data_source = crud.data_source.create(
        db_session, obj_in=schemas.DataSourceCreate(**data_source_data)
    )
    return data_source


@pytest.fixture
def test_template(db_session: Session, test_user: User) -> Template:
    """Create a test template in the database"""
    template_data = {
        "name": "Integration Test Template",
        "description": "Template for integration testing",
        "content": "Test template with {{placeholder}} for integration testing",
        "is_active": True,
        "user_id": test_user.id,
    }
    template = crud.template.create(
        db_session, obj_in=schemas.TemplateCreate(**template_data)
    )
    return template


@pytest.fixture
def test_etl_job(
    db_session: Session, test_user: User, test_data_source: DataSource
) -> ETLJob:
    """Create a test ETL job in the database"""
    etl_job_data = {
        "name": "Integration Test ETL Job",
        "description": "ETL job for integration testing",
        "source_id": test_data_source.id,
        "schedule": "0 0 * * *",  # Daily at midnight
        "is_active": True,
        "user_id": test_user.id,
    }
    etl_job = crud.etl_job.create(
        db_session, obj_in=schemas.ETLJobCreate(**etl_job_data)
    )
    return etl_job


@pytest.fixture
def authenticated_client(client, test_user: User):
    """Create an authenticated test client using admin/password"""
    print("TEST ROUTES:", [route.path for route in client.app.routes])
    login_data = {"username": "admin", "password": "password"}
    response = client.post(
        "/api/v1/auth/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print("LOGIN RESPONSE:", response.json())
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def admin_client(client, test_superuser: User):
    """Create an authenticated admin test client"""
    # Login to get access token
    login_data = {"username": test_superuser.username, "password": "adminpassword123"}
    response = client.post("/api/auth/access-token", data=login_data)
    token = response.json()["access_token"]

    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def sample_database_data() -> Dict[str, Any]:
    """Sample data for database integration tests"""
    return {
        "users": [
            {"username": "user1", "email": "user1@example.com", "password": "pass1", "is_superuser": False},
            {"username": "user2", "email": "user2@example.com", "password": "pass2", "is_superuser": False},
            {"username": "admin", "email": "admin@example.com", "password": "adminpass", "is_superuser": True},
        ],
        "data_sources": [
            {
                "name": "Source 1",
                "description": "First test source",
                "source_type": "database",
                "connection_string": "sqlite:///test1.db",
            },
            {
                "name": "Source 2",
                "description": "Second test source",
                "source_type": "api",
                "connection_string": "https://api.example.com",
            },
        ],
        "templates": [
            {
                "name": "Template 1",
                "description": "First test template",
                "content": "Template with {{data}} placeholder",
            },
            {
                "name": "Template 2",
                "description": "Second test template",
                "content": "Another template with {{value}} and {{date}}",
            },
        ],
    }


@pytest.fixture
def cleanup_database(db_session: Session):
    """Fixture to clean up database after integration tests"""
    yield
    # Clean up any test data that might persist
    # This runs after the test completes
    pass


# Test data management utilities
@pytest.fixture
def integration_test_db(db_session: Session):
    """Database session specifically for integration tests with cleanup"""
    yield db_session
    # Additional cleanup for integration tests
    db_session.rollback()


@pytest.fixture
def mock_external_services():
    """Mock external services for integration tests"""
    from unittest.mock import patch
    with patch('app.services.ai_integration.llm_service.AIService') as mock_ai, \
         patch('app.services.notification.email_service.EmailService') as mock_email:
        # Configure default mock behaviors
        mock_ai.return_value.generate_content.return_value = {
            "content": "Mock AI generated content",
            "confidence": 0.85
        }
        mock_email.return_value.send_email.return_value = {
            "status": "sent",
            "message_id": "mock_message_id"
        }
        yield {
            "ai_service": mock_ai,
            "email_service": mock_email
        }


@pytest.fixture
def performance_monitor():
    """Monitor performance during integration tests"""
    import time
    import psutil
    import os
    
    start_time = time.time()
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    yield
    
    end_time = time.time()
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    execution_time = end_time - start_time
    memory_usage = end_memory - start_memory
    
    # Log performance metrics
    print(f"\nIntegration Test Performance:")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Memory usage: {memory_usage:.2f} MB")
    
    # Assert reasonable performance
    assert execution_time < 30.0, f"Test took too long: {execution_time:.2f}s"
    assert memory_usage < 100.0, f"Test used too much memory: {memory_usage:.2f}MB"


# Automatically mark all tests in this directory as integration tests
pytestmark = pytest.mark.integration
