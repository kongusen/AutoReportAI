import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.config import settings

# Fixtures will be imported from conftest.py automatically


def create_superuser_token(
    client: TestClient, db_session: Session, username: str = "admin"
) -> str:
    """Helper function to create a superuser and return access token"""
    superuser_data = {
        "username": username,
        "password": "password123",
        "is_superuser": True,
    }
    crud.user.create(db_session, obj_in=schemas.UserCreate(**superuser_data))

    login_data = {"username": username, "password": "password123"}
    response = client.post("/api/v1/auth/access-token", data=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_data_source(client: TestClient, db_session: Session) -> None:
    """Test creating a new data source"""
    token = create_superuser_token(client, db_session, "admin_ds1")
    headers = {"Authorization": f"Bearer {token}"}

    data_source_data = {
        "name": "test_database",
        "source_type": "sql",
        "db_query": "SELECT * FROM test_table",
    }

    response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["name"] == data_source_data["name"]
    assert content["source_type"] == data_source_data["source_type"]
    assert content["db_query"] == data_source_data["db_query"]
    assert "id" in content


def test_get_data_sources(client: TestClient, db_session: Session) -> None:
    """Test retrieving data sources list"""
    token = create_superuser_token(client, db_session, "admin_ds2")
    headers = {"Authorization": f"Bearer {token}"}

    # First create a data source
    data_source_data = {
        "name": "test_api_source",
        "source_type": "api",
        "api_url": "https://api.example.com/data",
        "api_method": "GET",
        "api_headers": {"Authorization": "Bearer token123"},
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200

    # Now get the list
    response = client.get(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
    )

    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) >= 1

    # Check if our created data source is in the list
    source_names = [source["name"] for source in content]
    assert "test_api_source" in source_names


def test_test_data_source_connection_csv(
    client: TestClient, db_session: Session
) -> None:
    """Test CSV data source connection"""
    token = create_superuser_token(client, db_session, "admin_csv_test")
    headers = {"Authorization": f"Bearer {token}"}

    # Create CSV data source
    data_source_data = {
        "name": "test_csv_source",
        "source_type": "csv",
        "file_path": "tests/test_data/csv_data/sample_data.csv",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Test connection
    response = client.post(
        f"{settings.API_V1_STR}/data-sources/{source_id}/test",
        headers=headers,
    )
    assert response.status_code == 200
    assert "successful" in response.json()["msg"]


def test_test_data_source_connection_sql_invalid(
    client: TestClient, db_session: Session
) -> None:
    """Test SQL data source connection with invalid connection string"""
    token = create_superuser_token(client, db_session, "admin_sql_test")
    headers = {"Authorization": f"Bearer {token}"}

    # Create SQL data source with invalid connection string
    data_source_data = {
        "name": "test_sql_source",
        "source_type": "sql",
        "connection_string": "postgresql://invalid:invalid@localhost:5432/invalid",
        "db_query": "SELECT 1",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Test connection (should fail)
    response = client.post(
        f"{settings.API_V1_STR}/data-sources/{source_id}/test",
        headers=headers,
    )
    assert response.status_code == 400
    assert "failed" in response.json()["detail"]


def test_test_data_source_connection_api_invalid(
    client: TestClient, db_session: Session
) -> None:
    """Test API data source connection with invalid URL"""
    token = create_superuser_token(client, db_session, "admin_api_test")
    headers = {"Authorization": f"Bearer {token}"}

    # Create API data source with invalid URL
    data_source_data = {
        "name": "test_api_source",
        "source_type": "api",
        "api_url": "https://invalid-url-that-does-not-exist.com/api/data",
        "api_method": "GET",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Test connection (should fail)
    response = client.post(
        f"{settings.API_V1_STR}/data-sources/{source_id}/test",
        headers=headers,
    )
    assert response.status_code == 400
    assert "failed" in response.json()["detail"]


def test_preview_data_source_csv(client: TestClient, db_session: Session) -> None:
    """Test CSV data source preview"""
    token = create_superuser_token(client, db_session, "admin_csv_preview")
    headers = {"Authorization": f"Bearer {token}"}

    # Create CSV data source
    data_source_data = {
        "name": "test_csv_preview",
        "source_type": "csv",
        "file_path": "tests/test_data/csv_data/sample_data.csv",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Preview data
    response = client.get(
        f"{settings.API_V1_STR}/data-sources/{source_id}/preview",
        headers=headers,
    )
    assert response.status_code == 200
    preview_data = response.json()

    assert "columns" in preview_data
    assert "data" in preview_data
    assert "row_count" in preview_data
    assert preview_data["row_count"] > 0
    assert "id" in preview_data["columns"]
    assert "name" in preview_data["columns"]


def test_get_data_source_by_id(client: TestClient, db_session: Session) -> None:
    """Test getting a specific data source by ID"""
    token = create_superuser_token(client, db_session, "admin_get_by_id")
    headers = {"Authorization": f"Bearer {token}"}

    # Create data source
    data_source_data = {
        "name": "test_get_by_id",
        "source_type": "csv",
        "file_path": "tests/test_data/csv_data/sample_data.csv",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Get by ID
    response = client.get(
        f"{settings.API_V1_STR}/data-sources/{source_id}",
        headers=headers,
    )
    assert response.status_code == 200
    source_data = response.json()
    assert source_data["id"] == source_id
    assert source_data["name"] == "test_get_by_id"


def test_update_data_source_with_connection_string(
    client: TestClient, db_session: Session
) -> None:
    """Test updating a data source with connection string"""
    token = create_superuser_token(client, db_session, "admin_update_conn")
    headers = {"Authorization": f"Bearer {token}"}

    # Create SQL data source
    data_source_data = {
        "name": "test_update_conn",
        "source_type": "sql",
        "connection_string": "postgresql://user:pass@localhost:5432/db1",
        "db_query": "SELECT 1",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Update connection string
    update_data = {"connection_string": "postgresql://user:pass@localhost:5432/db2"}

    update_response = client.put(
        f"{settings.API_V1_STR}/data-sources/{source_id}",
        headers=headers,
        json=update_data,
    )
    assert update_response.status_code == 200
    updated_source = update_response.json()
    assert (
        updated_source["connection_string"]
        == "postgresql://user:pass@localhost:5432/db2"
    )


def test_get_data_source_not_found(client: TestClient, db_session: Session) -> None:
    """Test retrieving a non-existent data source"""
    token = create_superuser_token(client, db_session, "admin_ds4")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        f"{settings.API_V1_STR}/data-sources/999999",
        headers=headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_update_data_source(client: TestClient, db_session: Session) -> None:
    """Test updating a data source"""
    token = create_superuser_token(client, db_session, "admin_ds5")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a data source first
    data_source_data = {
        "name": "test_update_source",
        "source_type": "sql",
        "db_query": "SELECT * FROM original_table",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    created_source = create_response.json()
    source_id = created_source["id"]

    # Update the data source
    update_data = {
        "db_query": "SELECT * FROM updated_table",
        "api_url": "https://api.updated.com",
    }

    response = client.put(
        f"{settings.API_V1_STR}/data-sources/{source_id}",
        headers=headers,
        json=update_data,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["id"] == source_id
    assert content["db_query"] == update_data["db_query"]
    assert content["api_url"] == update_data["api_url"]
    # Name should remain unchanged
    assert content["name"] == data_source_data["name"]


def test_update_data_source_not_found(client: TestClient, db_session: Session) -> None:
    """Test updating a non-existent data source"""
    token = create_superuser_token(client, db_session, "admin_ds6")
    headers = {"Authorization": f"Bearer {token}"}

    update_data = {"db_query": "SELECT * FROM updated_table"}

    response = client.put(
        f"{settings.API_V1_STR}/data-sources/999999",
        headers=headers,
        json=update_data,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_delete_data_source(client: TestClient, db_session: Session) -> None:
    """Test deleting a data source"""
    token = create_superuser_token(client, db_session, "admin_ds7")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a data source first
    data_source_data = {
        "name": "test_delete_source",
        "source_type": "api",
        "api_url": "https://api.example.com/delete-test",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert create_response.status_code == 200
    created_source = create_response.json()
    source_id = created_source["id"]

    # Delete the data source
    response = client.delete(
        f"{settings.API_V1_STR}/data-sources/{source_id}",
        headers=headers,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["id"] == source_id

    # Verify it's deleted by trying to get it
    get_response = client.get(
        f"{settings.API_V1_STR}/data-sources/{source_id}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_delete_data_source_not_found(client: TestClient, db_session: Session) -> None:
    """Test deleting a non-existent data source"""
    token = create_superuser_token(client, db_session, "admin_ds8")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        f"{settings.API_V1_STR}/data-sources/999999",
        headers=headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_create_data_source_duplicate_name(
    client: TestClient, db_session: Session
) -> None:
    """Test creating a data source with duplicate name"""
    token = create_superuser_token(client, db_session, "admin_ds9")
    headers = {"Authorization": f"Bearer {token}"}

    data_source_data = {
        "name": "duplicate_name_test",
        "source_type": "sql",
        "db_query": "SELECT * FROM test_table",
    }

    # Create first data source
    response1 = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )
    assert response1.status_code == 200

    # Try to create second data source with same name
    data_source_data["db_query"] = "SELECT * FROM another_table"
    response2 = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )

    # This should fail due to unique constraint
    assert response2.status_code == 400 or response2.status_code == 422


def test_create_data_source_invalid_name(
    client: TestClient, db_session: Session
) -> None:
    """Test creating a data source with invalid name"""
    token = create_superuser_token(client, db_session, "admin_ds10")
    headers = {"Authorization": f"Bearer {token}"}

    # Test with empty name
    data_source_data = {
        "name": "",
        "source_type": "sql",
        "db_query": "SELECT * FROM test_table",
    }

    response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )

    assert response.status_code == 422

    # Test with invalid characters
    data_source_data["name"] = "invalid@name#"
    response = client.post(
        f"{settings.API_V1_STR}/data-sources/",
        headers=headers,
        json=data_source_data,
    )

    assert response.status_code == 422
