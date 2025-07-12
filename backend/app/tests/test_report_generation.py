import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, schemas
from app.tests.conftest import client, db_session
from app.core.config import settings


def create_superuser_token(client: TestClient, db_session: Session, username: str) -> str:
    """Helper function to create a superuser and return access token"""
    # Create superuser
    superuser_data = {
        "username": username,
        "password": "password123",
        "is_superuser": True
    }
    superuser = crud.user.create(db_session, obj_in=schemas.UserCreate(**superuser_data))
    
    # Login to get access token
    login_data = {
        "username": username,
        "password": "password123"
    }
    response = client.post("/api/v1/auth/access-token", data=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_test_report_pipeline(client: TestClient, db_session: Session):
    """Test the report generation pipeline health check"""
    token = create_superuser_token(client, db_session, "admin_report_test")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"{settings.API_V1_STR}/reports/test",
        headers=headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "pipeline_status" in result
    assert "components" in result
    assert "ai_service" in result["components"]
    assert "template_parser" in result["components"]
    assert "word_generator" in result["components"]
    assert "composition_service" in result["components"]


def test_validate_report_configuration_missing_template(client: TestClient, db_session: Session):
    """Test report configuration validation with missing template"""
    token = create_superuser_token(client, db_session, "admin_report_validate")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a data source
    data_source = crud.data_source.create(
        db_session,
        obj_in=schemas.DataSourceCreate(
            name="test_report_data_source",
            source_type="csv",
            file_path="test_data.csv"
        )
    )
    
    # Try to validate with non-existent template
    response = client.post(
        f"{settings.API_V1_STR}/reports/validate",
        headers=headers,
        params={
            "template_id": 999999,
            "data_source_id": data_source.id
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "valid" in result
    assert result["valid"] is False
    assert "errors" in result
    assert len(result["errors"]) > 0
    assert "Template not found" in result["errors"]


def test_validate_report_configuration_missing_data_source(client: TestClient, db_session: Session):
    """Test report configuration validation with missing data source"""
    token = create_superuser_token(client, db_session, "admin_report_validate2")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a template
    template = crud.template.create(
        db_session,
        obj_in=schemas.TemplateCreate(
            name="test_report_template",
            description="Test template"
        ),
        file_path="test_template.txt",
        parsed_structure={"placeholders": []}
    )
    
    # Try to validate with non-existent data source
    response = client.post(
        f"{settings.API_V1_STR}/reports/validate",
        headers=headers,
        params={
            "template_id": template.id,
            "data_source_id": 999999
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "valid" in result
    assert result["valid"] is False
    assert "errors" in result
    assert len(result["errors"]) > 0
    assert "Data source not found" in result["errors"]


def test_get_generation_status(client: TestClient, db_session: Session):
    """Test getting report generation status"""
    token = create_superuser_token(client, db_session, "admin_report_status")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(
        f"{settings.API_V1_STR}/reports/status/123",
        headers=headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "task_id" in result
    assert result["task_id"] == 123
    assert "status" in result
    assert "message" in result


def test_generate_report_missing_task(client: TestClient, db_session: Session):
    """Test report generation with missing task"""
    token = create_superuser_token(client, db_session, "admin_report_generate")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"{settings.API_V1_STR}/reports/generate",
        headers=headers,
        params={
            "task_id": 999999,
            "template_id": 1,
            "data_source_id": 1
        }
    )
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_preview_report_data_missing_template(client: TestClient, db_session: Session):
    """Test report data preview with missing template"""
    token = create_superuser_token(client, db_session, "admin_report_preview")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(
        f"{settings.API_V1_STR}/reports/preview",
        headers=headers,
        params={
            "template_id": 999999,
            "data_source_id": 1,
            "limit": 5
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "error" in result
    assert "Template not found" in result["error"] 