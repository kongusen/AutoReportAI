"""
Base test fixtures for the application.

Provides common test data and fixtures used across all test categories.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List


class TestDataFactory:
    """Factory class for generating test data."""

    @staticmethod
    def create_user(
        username: str = "testuser",
        email: str = "test@example.com",
        is_superuser: bool = False,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """Create a user with specified attributes."""
        return {
            "id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "full_name": f"{username.title()} User",
            "is_active": is_active,
            "is_superuser": is_superuser,
            "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    @staticmethod
    def create_data_source(
        name: str = "Test Data Source",
        source_type: str = "csv",
        file_path: str = "tests/test_data/csv_data/sample_data.csv",
    ) -> Dict[str, Any]:
        """Create a data source with specified attributes."""
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": f"{name} for testing",
            "source_type": source_type,
            "connection_string": file_path,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    @staticmethod
    def create_template(
        name: str = "Test Template", content: str = "Test content with {{placeholder}}"
    ) -> Dict[str, Any]:
        """Create a template with specified attributes."""
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": f"{name} for testing",
            "content": content,
            "file_path": f"{name.lower().replace(' ', '_')}.txt",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    @staticmethod
    def create_etl_job(
        name: str = "Test ETL Job", source_id: str = None
    ) -> Dict[str, Any]:
        """Create an ETL job with specified attributes."""
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": f"{name} for testing",
            "source_id": source_id or str(uuid.uuid4()),
            "schedule": "0 0 * * *",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }


# Common test data sets
SAMPLE_USERS = [
    TestDataFactory.create_user("user1", "user1@test.com"),
    TestDataFactory.create_user("user2", "user2@test.com"),
    TestDataFactory.create_user("admin", "admin@test.com", is_superuser=True),
]

SAMPLE_DATA_SOURCES = [
    TestDataFactory.create_data_source("CSV Source", "csv", "sample.csv"),
    TestDataFactory.create_data_source(
        "Database Source", "database", "postgresql://localhost/test"
    ),
    TestDataFactory.create_data_source(
        "API Source", "api", "https://api.example.com/data"
    ),
]

SAMPLE_TEMPLATES = [
    TestDataFactory.create_template("Basic Template", "Hello {{name}}!"),
    TestDataFactory.create_template(
        "Report Template", "Report for {{period}}: {{data}}"
    ),
]
