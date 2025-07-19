"""
Unit test specific configuration and fixtures.

Unit tests should be fast and isolated, with all external dependencies mocked.
This module provides fixtures and utilities specific to unit testing.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests"""
    mock_session = Mock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.first.return_value = None
    mock_session.all.return_value = []
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    return mock_session


@pytest.fixture
def mock_ai_service():
    """Mock AI service for unit tests"""
    mock_service = Mock()
    mock_service.generate_text.return_value = "Generated text response"
    mock_service.analyze_data.return_value = {"analysis": "test result"}
    return mock_service


@pytest.fixture
def mock_email_service():
    """Mock email service for unit tests"""
    mock_service = Mock()
    mock_service.send_email.return_value = True
    mock_service.send_notification.return_value = True
    return mock_service


@pytest.fixture
def mock_file_system():
    """Mock file system operations for unit tests"""
    mock_fs = Mock()
    mock_fs.read_file.return_value = "file content"
    mock_fs.write_file.return_value = True
    mock_fs.delete_file.return_value = True
    mock_fs.file_exists.return_value = True
    return mock_fs


@pytest.fixture
def sample_json_data() -> Dict[str, Any]:
    """Sample JSON data for unit tests"""
    return {
        "id": 1,
        "name": "Test Item",
        "data": {"field1": "value1", "field2": 42, "field3": True},
        "items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}],
    }


@pytest.fixture
def sample_csv_data() -> str:
    """Sample CSV data for unit tests"""
    return """id,name,value
1,Item 1,100
2,Item 2,200
3,Item 3,300"""


@pytest.fixture
def mock_external_api():
    """Mock external API responses for unit tests"""
    mock_api = Mock()
    mock_api.get.return_value.status_code = 200
    mock_api.get.return_value.json.return_value = {"status": "success", "data": {}}
    mock_api.post.return_value.status_code = 201
    mock_api.post.return_value.json.return_value = {"status": "created", "id": 1}
    return mock_api


# Automatically mark all tests in this directory as unit tests
pytestmark = pytest.mark.unit
