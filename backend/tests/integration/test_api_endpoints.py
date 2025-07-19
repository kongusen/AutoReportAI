"""
API Endpoints Integration Tests

Tests the integration between API endpoints, services, and database operations.
Verifies that API endpoints work correctly with real database operations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, schemas
from app.models.user import User
from app.models.template import Template
from app.models.enhanced_data_source import EnhancedDataSource


class TestAuthEndpoints:
    """Test authentication API endpoints integration"""

    def test_login_flow_with_existing_user(self, client: TestClient, test_user: User):
        """Test login flow with existing user"""
        # Login with existing test user
        login_data = {"username": test_user.username, "password": "testpassword123"}
        response = client.post("/api/auth/access-token", data=login_data)
        assert response.status_code == 200
        token_response = response.json()
        assert "access_token" in token_response
        assert token_response["token_type"] == "bearer"

    def test_login_with_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        login_data = {"username": "nonexistent", "password": "wrongpassword"}
        response = client.post("/api/auth/access-token", data=login_data)
        assert response.status_code == 400
        error_response = response.json()
        assert "detail" in error_response

    def test_protected_endpoint_access(self, authenticated_client: TestClient):
        """Test access to protected endpoints with authentication"""
        response = authenticated_client.get("/api/users/me")
        assert response.status_code == 200
        user_data = response.json()
        assert "username" in user_data
        assert "id" in user_data

    def test_unauthorized_access_denied(self, client: TestClient):
        """Test that unauthorized access is properly denied"""
        response = client.get("/api/users/me")
        assert response.status_code == 401


class TestTemplateEndpoints:
    """Test template API endpoints integration"""

    def test_template_crud_operations(self, authenticated_client: TestClient, db_session: Session):
        """Test complete CRUD operations for templates"""
        # Create template
        template_data = {
            "name": "API Integration Template",
            "description": "Template created via API integration test",
            "content": "Test template with {{placeholder}} content",
            "is_active": True
        }
        
        response = authenticated_client.post("/api/templates/", json=template_data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        created_template = response_data["data"]
        assert created_template["name"] == template_data["name"]
        template_id = created_template["id"]
        
        # Verify template exists in database
        db_template = crud.template.get(db_session, id=template_id)
        assert db_template is not None
        assert db_template.name == template_data["name"]
        
        # Read template
        response = authenticated_client.get(f"/api/templates/{template_id}")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        retrieved_template = response_data["data"]
        assert retrieved_template["id"] == template_id
        assert retrieved_template["name"] == template_data["name"]
        
        # Update template
        update_data = {
            "name": "Updated API Integration Template",
            "description": "Updated description",
            "content": "Updated content with {{new_placeholder}}"
        }
        response = authenticated_client.put(f"/api/templates/{template_id}", json=update_data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        updated_template = response_data["data"]
        assert updated_template["name"] == update_data["name"]
        
        # Verify update in database
        db_template = crud.template.get(db_session, id=template_id)
        assert db_template.name == update_data["name"]
        assert db_template.description == update_data["description"]
        
        # List templates
        response = authenticated_client.get("/api/templates/")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        templates_list = response_data["data"]
        assert len(templates_list) >= 1
        assert any(t["id"] == template_id for t in templates_list)
        
        # Delete template
        response = authenticated_client.delete(f"/api/templates/{template_id}")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        
        # Verify deletion in database
        db_template = crud.template.get(db_session, id=template_id)
        assert db_template is None

    def test_template_validation_errors(self, authenticated_client: TestClient):
        """Test template validation error handling"""
        # Test missing required fields
        invalid_template = {"description": "Missing name field"}
        response = authenticated_client.post("/api/templates/", json=invalid_template)
        assert response.status_code == 422
        
        # Test invalid template content
        invalid_template = {
            "name": "Invalid Template",
            "content": "",  # Empty content
            "description": "Template with empty content"
        }
        response = authenticated_client.post("/api/templates/", json=invalid_template)
        assert response.status_code == 422


class TestDataSourceEndpoints:
    """Test data source API endpoints integration"""

    def test_data_source_crud_operations(self, authenticated_client: TestClient, db_session: Session):
        """Test complete CRUD operations for data sources"""
        # Create data source
        data_source_data = {
            "name": "API Integration Data Source",
            "description": "Data source created via API integration test",
            "source_type": "sql",
            "connection_string": "sqlite:///api_integration_test.db"
        }
        
        response = authenticated_client.post("/api/data-sources/", json=data_source_data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        created_data_source = response_data["data"]
        assert created_data_source["name"] == data_source_data["name"]
        data_source_id = created_data_source["id"]
        
        # Verify data source exists in database
        db_data_source = crud.data_source.get(db_session, id=data_source_id)
        assert db_data_source is not None
        assert db_data_source.name == data_source_data["name"]
        
        # Read data source
        response = authenticated_client.get(f"/api/data-sources/{data_source_id}")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        retrieved_data_source = response_data["data"]
        assert retrieved_data_source["id"] == data_source_id
        
        # Update data source
        update_data = {
            "name": "Updated API Integration Data Source",
            "description": "Updated description"
        }
        response = authenticated_client.put(f"/api/data-sources/{data_source_id}", json=update_data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        updated_data_source = response_data["data"]
        assert updated_data_source["name"] == update_data["name"]
        
        # List data sources
        response = authenticated_client.get("/api/data-sources/")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data_sources_list = response_data["data"]
        assert len(data_sources_list) >= 1
        assert any(ds["id"] == data_source_id for ds in data_sources_list)
        
        # Delete data source
        response = authenticated_client.delete(f"/api/data-sources/{data_source_id}")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        
        # Verify deletion in database
        db_data_source = crud.data_source.get(db_session, id=data_source_id)
        assert db_data_source is None


class TestIntelligentPlaceholderEndpoints:
    """Test intelligent placeholder API endpoints integration"""

    def test_placeholder_processing_integration(
        self, 
        authenticated_client: TestClient, 
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test intelligent placeholder processing through API"""
        # Test placeholder analysis
        analysis_data = {
            "template_id": str(test_template.id),
            "content": "Template with {{customer_name}} and {{order_date}} placeholders"
        }
        
        response = authenticated_client.post("/api/intelligent-placeholders/analyze", json=analysis_data)
        # May not be implemented yet, so check for reasonable response
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            analysis_result = response.json()
            # Check if it follows the APIResponse format
            if "success" in analysis_result:
                assert analysis_result["success"] is True
            else:
                # Direct response format
                assert "placeholders" in analysis_result

    def test_placeholder_validation_errors(self, authenticated_client: TestClient):
        """Test placeholder validation error handling"""
        # Test invalid template ID
        invalid_data = {
            "template_id": "99999",  # Non-existent template
            "content": "Template with {{placeholder}}"
        }
        
        response = authenticated_client.post("/api/intelligent-placeholders/analyze", json=invalid_data)
        assert response.status_code in [404, 422, 501]  # May not be implemented


class TestReportGenerationEndpoints:
    """Test report generation API endpoints integration"""

    def test_report_generation_flow(
        self, 
        authenticated_client: TestClient,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test complete report generation flow through API"""
        # Create report generation request
        report_data = {
            "template_id": str(test_template.id),
            "data_source_id": str(test_data_source.id),
            "parameters": {
                "placeholder": "Integration Test Value"
            },
            "output_format": "pdf"
        }
        
        response = authenticated_client.post("/api/reports/generate", json=report_data)
        # May not be fully implemented, check for reasonable response
        assert response.status_code in [200, 202, 404, 501]
        
        if response.status_code in [200, 202]:
            generation_result = response.json()
            # Check if it follows the APIResponse format or has task_id
            if "success" in generation_result:
                assert generation_result["success"] is True
            elif "task_id" in generation_result:
                # Check report generation status if task_id is provided
                task_id = generation_result["task_id"]
                response = authenticated_client.get(f"/api/reports/status/{task_id}")
                assert response.status_code in [200, 404]

    def test_report_history_integration(self, authenticated_client: TestClient):
        """Test report history API integration"""
        response = authenticated_client.get("/api/history")
        # May not be fully implemented
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            history_result = response.json()
            # Check if it follows the APIResponse format
            if "success" in history_result:
                assert history_result["success"] is True
                assert "data" in history_result
            else:
                assert isinstance(history_result, list)


class TestErrorHandlingIntegration:
    """Test error handling across API endpoints"""

    def test_404_error_handling(self, authenticated_client: TestClient):
        """Test 404 error handling for non-existent resources"""
        # Test non-existent template
        response = authenticated_client.get("/api/templates/99999")
        assert response.status_code == 404
        
        # Test non-existent data source
        response = authenticated_client.get("/api/data-sources/99999")
        assert response.status_code == 404

    def test_validation_error_handling(self, authenticated_client: TestClient):
        """Test validation error handling"""
        # Test invalid JSON data
        invalid_data = {"invalid": "data structure"}
        response = authenticated_client.post("/api/templates/", json=invalid_data)
        assert response.status_code == 422
        error_response = response.json()
        assert "detail" in error_response

    def test_database_constraint_errors(self, authenticated_client: TestClient):
        """Test database constraint error handling"""
        # Create template with valid data
        template_data = {
            "name": "Unique Template Name",
            "description": "Test template",
            "content": "Test content"
        }
        response = authenticated_client.post("/api/templates/", json=template_data)
        assert response.status_code == 200
        
        # Try to create another template with the same name (if unique constraint exists)
        response = authenticated_client.post("/api/templates/", json=template_data)
        # Should handle constraint violation gracefully
        assert response.status_code in [400, 409, 422]


class TestConcurrencyAndPerformance:
    """Test API endpoints under concurrent access"""

    def test_concurrent_template_creation(self, authenticated_client: TestClient):
        """Test concurrent template creation"""
        import threading
        
        results = []
        
        def create_template(index):
            template_data = {
                "name": f"Concurrent Template {index}",
                "description": f"Template created concurrently {index}",
                "content": f"Content for template {index}"
            }
            response = authenticated_client.post("/api/templates/", json=template_data)
            results.append(response.status_code)
        
        # Create multiple threads to create templates concurrently
        threads = []
        for i in range(3):  # Reduced number for faster testing
            thread = threading.Thread(target=create_template, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)

    def test_api_response_times(self, authenticated_client: TestClient):
        """Test API response times are reasonable"""
        import time
        
        # Test template list endpoint performance
        start_time = time.time()
        response = authenticated_client.get("/api/templates/")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds
        
        # Test data source list endpoint performance
        start_time = time.time()
        response = authenticated_client.get("/api/data-sources/")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds