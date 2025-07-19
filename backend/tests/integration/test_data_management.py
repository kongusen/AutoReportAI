"""
Test Data Management for Integration Tests

Provides utilities and fixtures for automated test data management,
including setup, cleanup, and data factories for integration tests.
"""

import pytest
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import random
from datetime import datetime, timedelta

from app import crud, schemas
from app.models.user import User
from app.models.template import Template
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.etl_job import ETLJob
from app.models.placeholder_mapping import PlaceholderMapping
from app.models.report_history import ReportHistory


class TestDataFactory:
    """Factory for creating test data objects"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def create_user(self, **kwargs) -> User:
        """Create a test user with optional custom attributes"""
        default_data = {
            "username": f"testuser_{random.randint(1000, 9999)}",
            "email": f"testuser_{random.randint(1000, 9999)}@example.com",
            "password": "testpassword123",
            "is_superuser": False,
        }
        default_data.update(kwargs)
        
        user_data = schemas.UserCreate(**default_data)
        return crud.user.create(self.db_session, obj_in=user_data)
    
    def create_template(self, user: Optional[User] = None, **kwargs) -> Template:
        """Create a test template with optional custom attributes"""
        if user is None:
            user = self.create_user()
        
        default_data = {
            "name": f"Test Template {random.randint(1000, 9999)}",
            "description": f"Test template description {random.randint(1000, 9999)}",
            "content": self._generate_template_content(),
            "is_active": True,
            "user_id": user.id
        }
        default_data.update(kwargs)
        
        user_id = default_data.pop("user_id")
        template_data = schemas.TemplateCreate(**default_data)
        return crud.template.create(self.db_session, obj_in=template_data, user_id=user_id)
    
    def create_data_source(self, user: Optional[User] = None, **kwargs) -> EnhancedDataSource:
        """Create a test data source with optional custom attributes"""
        if user is None:
            user = self.create_user()
        
        source_types = ["sql", "csv", "api", "push"]
        default_data = {
            "name": f"Test Company {random.randint(1000, 9999)} Data Source",
            "description": f"Test data source description {random.randint(1000, 9999)}",
            "source_type": random.choice(source_types),
            "connection_string": self._generate_connection_string(),
            "is_active": True,
            "user_id": user.id
        }
        default_data.update(kwargs)
        
        data_source_data = schemas.EnhancedDataSourceCreate(**default_data)
        return crud.enhanced_data_source.create(self.db_session, obj_in=data_source_data)
    
    def create_etl_job(
        self, 
        user: Optional[User] = None, 
        data_source: Optional[EnhancedDataSource] = None,
        **kwargs
    ) -> ETLJob:
        """Create a test ETL job with optional custom attributes"""
        if user is None:
            user = self.create_user()
        if data_source is None:
            data_source = self.create_data_source(user=user)
        
        schedules = ["0 0 * * *", "0 12 * * *", "0 */6 * * *", "0 0 * * 0"]
        default_data = {
            "name": f"Test ETL Job {random.randint(1000, 9999)}",
            "description": f"Test ETL job description {random.randint(1000, 9999)}",
            "source_id": data_source.id,
            "schedule": random.choice(schedules),
            "is_active": True,
            "user_id": user.id
        }
        default_data.update(kwargs)
        
        etl_job_data = schemas.ETLJobCreate(**default_data)
        return crud.etl_job.create(self.db_session, obj_in=etl_job_data)
    
    def create_placeholder_mapping(
        self,
        template: Optional[Template] = None,
        data_source: Optional[EnhancedDataSource] = None,
        user: Optional[User] = None,
        **kwargs
    ) -> PlaceholderMapping:
        """Create a test placeholder mapping with optional custom attributes"""
        if user is None:
            user = self.create_user()
        if template is None:
            template = self.create_template(user=user)
        if data_source is None:
            data_source = self.create_data_source(user=user)
        
        field_types = ["string", "integer", "decimal", "date", "boolean"]
        default_data = {
            "template_id": template.id,
            "data_source_id": data_source.id,
            "placeholder_name": f"test_placeholder_{random.randint(1000, 9999)}",
            "field_name": f"test_field_{random.randint(1000, 9999)}",
            "field_type": random.choice(field_types),
            "user_id": user.id
        }
        default_data.update(kwargs)
        
        mapping_data = schemas.PlaceholderMappingCreate(**default_data)
        return crud.placeholder_mapping.create(self.db_session, obj_in=mapping_data)
    
    def create_report_history(
        self,
        template: Optional[Template] = None,
        data_source: Optional[EnhancedDataSource] = None,
        user: Optional[User] = None,
        **kwargs
    ) -> ReportHistory:
        """Create a test report history entry with optional custom attributes"""
        if user is None:
            user = self.create_user()
        if template is None:
            template = self.create_template(user=user)
        if data_source is None:
            data_source = self.create_data_source(user=user)
        
        statuses = ["pending", "processing", "completed", "failed"]
        formats = ["pdf", "docx", "html", "csv"]
        default_data = {
            "template_id": template.id,
            "data_source_id": data_source.id,
            "status": random.choice(statuses),
            "output_format": random.choice(formats),
            "file_path": f"/tmp/reports/report_{random.randint(1000, 9999)}.{random.choice(formats)}",
            "user_id": user.id
        }
        default_data.update(kwargs)
        
        report_data = schemas.ReportHistoryCreate(**default_data)
        return crud.report_history.create(self.db_session, obj_in=report_data)
    
    def _generate_template_content(self) -> str:
        """Generate realistic template content with placeholders"""
        placeholders = [
            "{{customer_name}}", "{{order_date}}", "{{total_amount}}",
            "{{product_name}}", "{{quantity}}", "{{description}}",
            "{{start_date}}", "{{end_date}}", "{{summary}}"
        ]
        
        content_parts = [
            "This is a test template sentence.",
            f"Customer: {random.choice(placeholders)}",
            f"Date: {random.choice(placeholders)}",
            "This is a test paragraph with sample content for the template.",
            f"Total: {random.choice(placeholders)}",
            "This is another test sentence."
        ]
        
        return "\n\n".join(content_parts)
    
    def _generate_connection_string(self) -> str:
        """Generate realistic connection strings for different source types"""
        connection_types = [
            "sqlite:///test_database.db",
            "postgresql://user:password@localhost:5432/testdb",
            "mysql://user:password@localhost:3306/testdb",
            "https://api.example.com/v1/data",
            "file:///path/to/data/file.csv"
        ]
        return random.choice(connection_types)


class TestDataManager:
    """Manager for test data lifecycle and cleanup"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.factory = TestDataFactory(db_session)
        self.created_objects = {
            "users": [],
            "templates": [],
            "data_sources": [],
            "etl_jobs": [],
            "placeholder_mappings": [],
            "report_histories": []
        }
    
    def create_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Create predefined test scenarios with related data"""
        scenarios = {
            "basic_user_workflow": self._create_basic_user_workflow,
            "complex_report_generation": self._create_complex_report_generation,
            "multi_user_environment": self._create_multi_user_environment,
            "etl_processing_scenario": self._create_etl_processing_scenario,
            "placeholder_mapping_scenario": self._create_placeholder_mapping_scenario
        }
        
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        return scenarios[scenario_name]()
    
    def _create_basic_user_workflow(self) -> Dict[str, Any]:
        """Create basic user workflow test data"""
        user = self.factory.create_user()
        template = self.factory.create_template(user=user)
        data_source = self.factory.create_data_source(user=user)
        
        self._track_objects(users=[user], templates=[template], data_sources=[data_source])
        
        return {
            "user": user,
            "template": template,
            "data_source": data_source
        }
    
    def _create_complex_report_generation(self) -> Dict[str, Any]:
        """Create complex report generation test data"""
        user = self.factory.create_user()
        
        # Create multiple templates
        templates = [
            self.factory.create_template(user=user, name="Monthly Report Template"),
            self.factory.create_template(user=user, name="Quarterly Analysis Template"),
            self.factory.create_template(user=user, name="Annual Summary Template")
        ]
        
        # Create multiple data sources
        data_sources = [
            self.factory.create_data_source(user=user, source_type="database"),
            self.factory.create_data_source(user=user, source_type="api"),
            self.factory.create_data_source(user=user, source_type="file")
        ]
        
        # Create placeholder mappings
        mappings = []
        for template in templates:
            for data_source in data_sources:
                mapping = self.factory.create_placeholder_mapping(
                    template=template,
                    data_source=data_source,
                    user=user
                )
                mappings.append(mapping)
        
        # Create report history
        reports = []
        for template in templates:
            for data_source in data_sources:
                report = self.factory.create_report_history(
                    template=template,
                    data_source=data_source,
                    user=user
                )
                reports.append(report)
        
        self._track_objects(
            users=[user],
            templates=templates,
            data_sources=data_sources,
            placeholder_mappings=mappings,
            report_histories=reports
        )
        
        return {
            "user": user,
            "templates": templates,
            "data_sources": data_sources,
            "mappings": mappings,
            "reports": reports
        }
    
    def _create_multi_user_environment(self) -> Dict[str, Any]:
        """Create multi-user environment test data"""
        # Create different types of users
        admin_user = self.factory.create_user(is_superuser=True, username="admin_user")
        regular_users = [
            self.factory.create_user(username=f"user_{i}") for i in range(3)
        ]
        
        all_users = [admin_user] + regular_users
        
        # Create shared and private resources
        shared_templates = [
            self.factory.create_template(user=admin_user, name="Shared Template 1"),
            self.factory.create_template(user=admin_user, name="Shared Template 2")
        ]
        
        private_templates = []
        private_data_sources = []
        
        for user in regular_users:
            # Each user has private templates and data sources
            user_templates = [
                self.factory.create_template(user=user, name=f"{user.username} Private Template")
            ]
            user_data_sources = [
                self.factory.create_data_source(user=user, name=f"{user.username} Data Source")
            ]
            
            private_templates.extend(user_templates)
            private_data_sources.extend(user_data_sources)
        
        self._track_objects(
            users=all_users,
            templates=shared_templates + private_templates,
            data_sources=private_data_sources
        )
        
        return {
            "admin_user": admin_user,
            "regular_users": regular_users,
            "shared_templates": shared_templates,
            "private_templates": private_templates,
            "private_data_sources": private_data_sources
        }
    
    def _create_etl_processing_scenario(self) -> Dict[str, Any]:
        """Create ETL processing scenario test data"""
        user = self.factory.create_user()
        
        # Create data sources for ETL
        data_sources = [
            self.factory.create_data_source(
                user=user,
                source_type="database",
                name="Primary Database"
            ),
            self.factory.create_data_source(
                user=user,
                source_type="api",
                name="External API"
            ),
            self.factory.create_data_source(
                user=user,
                source_type="file",
                name="CSV Data Files"
            )
        ]
        
        # Create ETL jobs for each data source
        etl_jobs = []
        for i, data_source in enumerate(data_sources):
            job = self.factory.create_etl_job(
                user=user,
                data_source=data_source,
                name=f"ETL Job {i+1}",
                schedule="0 0 * * *" if i == 0 else "0 12 * * *"
            )
            etl_jobs.append(job)
        
        self._track_objects(
            users=[user],
            data_sources=data_sources,
            etl_jobs=etl_jobs
        )
        
        return {
            "user": user,
            "data_sources": data_sources,
            "etl_jobs": etl_jobs
        }
    
    def _create_placeholder_mapping_scenario(self) -> Dict[str, Any]:
        """Create placeholder mapping scenario test data"""
        user = self.factory.create_user()
        
        # Create template with specific placeholders
        template = self.factory.create_template(
            user=user,
            name="Customer Report Template",
            content="""
            Customer Report
            
            Customer Name: {{customer_name}}
            Order Date: {{order_date}}
            Total Amount: {{total_amount}}
            Product: {{product_name}}
            Quantity: {{quantity}}
            
            Summary: {{summary}}
            """
        )
        
        # Create data source with corresponding fields
        data_source = self.factory.create_data_source(
            user=user,
            name="Customer Database",
            source_type="database"
        )
        
        # Create placeholder mappings
        placeholder_configs = [
            {"placeholder_name": "customer_name", "field_name": "customer_full_name", "field_type": "string"},
            {"placeholder_name": "order_date", "field_name": "order_timestamp", "field_type": "date"},
            {"placeholder_name": "total_amount", "field_name": "order_total", "field_type": "decimal"},
            {"placeholder_name": "product_name", "field_name": "product_title", "field_type": "string"},
            {"placeholder_name": "quantity", "field_name": "order_quantity", "field_type": "integer"},
            {"placeholder_name": "summary", "field_name": "order_notes", "field_type": "string"}
        ]
        
        mappings = []
        for config in placeholder_configs:
            mapping = self.factory.create_placeholder_mapping(
                template=template,
                data_source=data_source,
                user=user,
                **config
            )
            mappings.append(mapping)
        
        self._track_objects(
            users=[user],
            templates=[template],
            data_sources=[data_source],
            placeholder_mappings=mappings
        )
        
        return {
            "user": user,
            "template": template,
            "data_source": data_source,
            "mappings": mappings
        }
    
    def _track_objects(self, **kwargs):
        """Track created objects for cleanup"""
        for object_type, objects in kwargs.items():
            if object_type in self.created_objects:
                self.created_objects[object_type].extend(objects)
    
    def cleanup_all(self):
        """Clean up all created test data"""
        # Clean up in reverse dependency order
        cleanup_order = [
            ("report_histories", crud.report_history),
            ("placeholder_mappings", crud.placeholder_mapping),
            ("etl_jobs", crud.etl_job),
            ("templates", crud.template),
            ("data_sources", crud.enhanced_data_source),
            ("users", crud.user)
        ]
        
        for object_type, crud_service in cleanup_order:
            objects = self.created_objects.get(object_type, [])
            for obj in objects:
                try:
                    crud_service.remove(self.db_session, id=obj.id)
                except Exception as e:
                    # Log error but continue cleanup
                    print(f"Error cleaning up {object_type} {obj.id}: {e}")
        
        # Clear tracking
        for object_type in self.created_objects:
            self.created_objects[object_type].clear()


@pytest.fixture
def test_data_factory(db_session: Session) -> TestDataFactory:
    """Provide test data factory fixture"""
    return TestDataFactory(db_session)


@pytest.fixture
def test_data_manager(db_session: Session) -> TestDataManager:
    """Provide test data manager fixture with automatic cleanup"""
    manager = TestDataManager(db_session)
    yield manager
    manager.cleanup_all()


@pytest.fixture
def basic_test_scenario(test_data_manager: TestDataManager) -> Dict[str, Any]:
    """Provide basic test scenario data"""
    return test_data_manager.create_test_scenario("basic_user_workflow")


@pytest.fixture
def complex_report_scenario(test_data_manager: TestDataManager) -> Dict[str, Any]:
    """Provide complex report generation scenario data"""
    return test_data_manager.create_test_scenario("complex_report_generation")


@pytest.fixture
def multi_user_scenario(test_data_manager: TestDataManager) -> Dict[str, Any]:
    """Provide multi-user environment scenario data"""
    return test_data_manager.create_test_scenario("multi_user_environment")


@pytest.fixture
def etl_scenario(test_data_manager: TestDataManager) -> Dict[str, Any]:
    """Provide ETL processing scenario data"""
    return test_data_manager.create_test_scenario("etl_processing_scenario")


@pytest.fixture
def placeholder_scenario(test_data_manager: TestDataManager) -> Dict[str, Any]:
    """Provide placeholder mapping scenario data"""
    return test_data_manager.create_test_scenario("placeholder_mapping_scenario")


class TestDataValidation:
    """Test data validation and integrity checks"""
    
    def test_data_factory_creates_valid_objects(self, test_data_factory: TestDataFactory):
        """Test that data factory creates valid objects"""
        # Test user creation
        user = test_data_factory.create_user()
        assert user.id is not None
        assert user.username is not None
        assert len(user.username) > 0
        
        # Test template creation
        template = test_data_factory.create_template(user=user)
        assert template.id is not None
        assert template.name is not None
        assert template.user_id == user.id
        
        # Test data source creation
        data_source = test_data_factory.create_data_source(user=user)
        assert data_source.id is not None
        assert data_source.name is not None
        assert data_source.user_id == user.id
    
    def test_scenario_data_integrity(self, basic_test_scenario: Dict[str, Any]):
        """Test that scenario data maintains referential integrity"""
        user = basic_test_scenario["user"]
        template = basic_test_scenario["template"]
        data_source = basic_test_scenario["data_source"]
        
        # Verify relationships
        assert template.user_id == user.id
        assert data_source.user_id == user.id
        
        # Verify objects exist in database
        assert template.user is not None
        assert data_source.user is not None
    
    def test_cleanup_removes_all_data(self, test_data_manager: TestDataManager, db_session: Session):
        """Test that cleanup removes all created data"""
        # Create test data
        scenario = test_data_manager.create_test_scenario("basic_user_workflow")
        user_id = scenario["user"].id
        template_id = scenario["template"].id
        data_source_id = scenario["data_source"].id
        
        # Verify data exists
        assert crud.user.get(db_session, id=user_id) is not None
        assert crud.template.get(db_session, id=template_id) is not None
        assert crud.enhanced_data_source.get(db_session, id=data_source_id) is not None
        
        # Cleanup
        test_data_manager.cleanup_all()
        
        # Verify data is removed
        assert crud.user.get(db_session, id=user_id) is None
        assert crud.template.get(db_session, id=template_id) is None
        assert crud.enhanced_data_source.get(db_session, id=data_source_id) is None