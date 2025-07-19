"""
End-to-end test specific configuration and fixtures.

E2E tests verify complete user workflows and system behavior with real
external dependencies and full system integration.
"""

import time
from typing import Any, Dict, Generator

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base


@pytest.fixture(scope="session")
def e2e_database():
    """Create a separate database for E2E tests"""
    engine = create_engine(settings.test_db_url)
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup after all E2E tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def api_base_url() -> str:
    """Base URL for API testing"""
    return "http://localhost:8000/api/v1"


@pytest.fixture
def wait_for_server(api_base_url: str):
    """Wait for the server to be ready before running E2E tests"""
    max_retries = 30
    retry_delay = 1

    for i in range(max_retries):
        try:
            response = requests.get(f"{api_base_url.replace('/api/v1', '')}/")
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                time.sleep(retry_delay)
            else:
                pytest.fail("Server is not responding after maximum retries")

    return False


@pytest.fixture
def e2e_user_credentials() -> Dict[str, str]:
    """Credentials for E2E test user"""
    return {"username": "e2e_test_user", "password": "e2e_test_password123"}


@pytest.fixture
def e2e_admin_credentials() -> Dict[str, str]:
    """Credentials for E2E test admin user"""
    return {"username": "e2e_admin_user", "password": "e2e_admin_password123"}


@pytest.fixture
def authenticated_session(
    api_base_url: str, e2e_user_credentials: Dict[str, str]
) -> requests.Session:
    """Create an authenticated requests session for E2E tests"""
    session = requests.Session()

    # Login to get access token
    login_response = session.post(
        f"{api_base_url}/auth/login", data=e2e_user_credentials
    )

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})

    return session


@pytest.fixture
def admin_session(
    api_base_url: str, e2e_admin_credentials: Dict[str, str]
) -> requests.Session:
    """Create an authenticated admin requests session for E2E tests"""
    session = requests.Session()

    # Login to get access token
    login_response = session.post(
        f"{api_base_url}/auth/login", data=e2e_admin_credentials
    )

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})

    return session


@pytest.fixture
def sample_workflow_data() -> Dict[str, Any]:
    """Sample data for complete workflow testing"""
    return {
        "data_source": {
            "name": "E2E Test Data Source",
            "description": "Data source for end-to-end testing",
            "source_type": "database",
            "connection_string": "sqlite:///e2e_test.db",
            "is_active": True,
        },
        "template": {
            "name": "E2E Test Template",
            "description": "Template for end-to-end testing",
            "content": "E2E test report with {{total_records}} records processed on {{date}}",
            "is_active": True,
        },
        "etl_job": {
            "name": "E2E Test ETL Job",
            "description": "ETL job for end-to-end testing",
            "schedule": "0 */6 * * *",  # Every 6 hours
            "is_active": True,
        },
    }


@pytest.fixture
def performance_thresholds() -> Dict[str, float]:
    """Performance thresholds for E2E tests"""
    return {
        "api_response_time": 2.0,  # seconds
        "report_generation_time": 60.0,  # seconds (increased for complex reports)
        "data_processing_time": 120.0,  # seconds (increased for large datasets)
        "file_upload_time": 10.0,  # seconds
        "intelligent_processing_time": 30.0,  # seconds
        "batch_processing_time": 180.0,  # seconds
        "ai_enhancement_time": 90.0,  # seconds
    }


@pytest.fixture
def cleanup_e2e_data(authenticated_session: requests.Session, api_base_url: str):
    """Clean up data created during E2E tests"""
    yield

    # Cleanup logic runs after each E2E test
    try:
        # Clean up test data sources
        response = authenticated_session.get(f"{api_base_url}/data-sources/")
        if response.status_code == 200:
            data_sources = response.json()
            for ds in data_sources:
                if "E2E Test" in ds.get("name", ""):
                    authenticated_session.delete(
                        f"{api_base_url}/data-sources/{ds['id']}"
                    )

        # Clean up test templates
        response = authenticated_session.get(f"{api_base_url}/templates/")
        if response.status_code == 200:
            templates = response.json()
            for template in templates:
                if "E2E Test" in template.get("name", ""):
                    authenticated_session.delete(
                        f"{api_base_url}/templates/{template['id']}"
                    )

        # Clean up test ETL jobs
        response = authenticated_session.get(f"{api_base_url}/etl-jobs/")
        if response.status_code == 200:
            etl_jobs = response.json()
            for job in etl_jobs:
                if "E2E Test" in job.get("name", ""):
                    authenticated_session.delete(f"{api_base_url}/etl-jobs/{job['id']}")

    except Exception as e:
        # Log cleanup errors but don't fail the test
        print(f"Warning: E2E cleanup failed: {e}")


# Automatically mark all tests in this directory as e2e tests
pytestmark = pytest.mark.e2e
