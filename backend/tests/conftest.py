"""
Global test configuration and fixtures for the AutoReportAI backend.

This module provides shared fixtures and configuration for all test categories:
- Unit tests: Fast, isolated tests with mocked dependencies
- Integration tests: Tests with real database connections and service integrations
- End-to-end tests: Full system tests with external dependencies
"""

import os
import tempfile
from typing import Any, Dict, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base

# Test configuration
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Create a test FastAPI app without startup events"""
    app = FastAPI(title=f"{settings.PROJECT_NAME} Test")
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    def read_root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} Test"}

    return app


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
    )
    return engine


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables for testing"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables) -> Generator[Session, None, None]:
    """
    Returns an sqlalchemy session with automatic rollback after each test.
    This ensures test isolation by rolling back all changes.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(test_app: FastAPI, db_session: Session) -> Generator[TestClient, None, None]:
    """
    Returns a TestClient for API testing.
    The database dependency is overridden to use the test database session.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client

    # Clean up dependency overrides
    test_app.dependency_overrides.clear()


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file for testing file operations"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "password": "testpassword123",
        "is_superuser": False,
    }


@pytest.fixture
def sample_superuser_data() -> Dict[str, Any]:
    """Sample superuser data for testing"""
    return {"username": "admin", "password": "adminpassword123", "is_superuser": True}


@pytest.fixture
def sample_data_source_data() -> Dict[str, Any]:
    """Sample data source data for testing"""
    return {
        "name": "Test Data Source",
        "description": "A test data source",
        "source_type": "database",
        "connection_string": "sqlite:///test.db",
        "is_active": True,
    }


@pytest.fixture
def sample_template_data() -> Dict[str, Any]:
    """Sample template data for testing"""
    return {
        "name": "Test Template",
        "description": "A test template",
        "content": "This is a test template with {{placeholder}}",
        "is_active": True,
    }


# Test markers for different test categories
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests - fast, isolated tests")
    config.addinivalue_line(
        "markers",
        "integration: Integration tests - tests with database/service integration",
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests - full system tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
