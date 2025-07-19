"""
Basic tests that don't require database connection.
"""

import pytest
from fastapi.testclient import TestClient


def test_import_main():
    """Test that we can import the main module."""
    from app.main import app

    assert app is not None


def test_basic_math():
    """Test basic functionality."""
    assert 1 + 1 == 2
    assert "hello" + " world" == "hello world"


def test_pydantic_models():
    """Test that Pydantic models can be imported."""
    from app.schemas.task import Task, TaskCreate
    from app.schemas.user import User, UserCreate

    # Test basic model creation
    user_data = {"username": "testuser", "email": "testuser@example.com", "password": "testpassword"}
    user_create = UserCreate(**user_data)
    assert user_create.username == "testuser"
    assert user_create.password == "testpassword"
    assert user_create.is_superuser == False
