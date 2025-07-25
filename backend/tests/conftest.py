"""
Global test configuration and fixtures for all test types
"""

import os
import tempfile
from typing import Generator, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings

# Test database configuration
@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup after tests
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture(scope="session")
def test_engine(test_db_path):
    """Create test database engine"""
    database_url = f"sqlite:///{test_db_path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database dependency"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Common test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User"
    }

@pytest.fixture
def sample_data_source_data():
    """Sample data source data for testing"""
    return {
        "name": "Test Data Source",
        "source_type": "database",
        "connection_string": "sqlite:///test.db",
        "description": "Test data source for testing",
        "config": {
            "host": "localhost",
            "port": 5432,
            "database": "testdb"
        }
    }

@pytest.fixture
def sample_template_data():
    """Sample template data for testing"""
    return {
        "name": "Test Template",
        "description": "Test template for testing",
        "content": "This is a test template with {{placeholder}}",
        "is_active": True
    }

@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "name": "Test Task",
        "description": "Test task for testing",
        "schedule": "0 0 * * *"
    }
