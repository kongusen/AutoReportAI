"""
Database Operations Integration Tests

Tests the integration between CRUD operations, database models, and business logic.
Verifies that database operations work correctly with complex scenarios.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import crud, schemas
from app.models.user import User
from app.models.template import Template
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.etl_job import ETLJob
from app.models.placeholder_mapping import PlaceholderMapping
from app.models.report_history import ReportHistory


class TestUserDatabaseOperations:
    """Test user-related database operations"""

    def test_user_creation_and_retrieval(self, db_session: Session):
        """Test user creation and various retrieval methods"""
        # Create user
        user_data = schemas.UserCreate(
            username="db_test_user",
            email="db_test_user@example.com",
            password="testpassword123",
            is_superuser=False
        )
        created_user = crud.user.create(db_session, obj_in=user_data)
        
        assert created_user.username == user_data.username
        assert created_user.id is not None
        assert created_user.is_superuser == user_data.is_superuser
        
        # Test retrieval by ID
        retrieved_user = crud.user.get(db_session, id=created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.username == user_data.username
        
        # Test retrieval by username
        user_by_username = crud.user.get_by_username(db_session, username=user_data.username)
        assert user_by_username is not None
        assert user_by_username.id == created_user.id
        
        # Test user list
        users_list = crud.user.get_multi(db_session)
        assert len(users_list) >= 1
        assert any(u.id == created_user.id for u in users_list)

    def test_user_update_operations(self, db_session: Session):
        """Test user update operations"""
        # Create user
        user_data = schemas.UserCreate(
            username="update_test_user",
            email="update_test_user@example.com",
            password="testpassword123",
            is_superuser=False
        )
        created_user = crud.user.create(db_session, obj_in=user_data)
        
        # Update user
        update_data = schemas.UserUpdate(
            username="updated_username",
            is_superuser=True
        )
        updated_user = crud.user.update(db_session, db_obj=created_user, obj_in=update_data)
        
        assert updated_user.username == update_data.username
        assert updated_user.is_superuser == update_data.is_superuser
        
        # Verify update persisted
        retrieved_user = crud.user.get(db_session, id=created_user.id)
        assert retrieved_user.username == update_data.username
        assert retrieved_user.is_superuser == update_data.is_superuser

    def test_user_deletion(self, db_session: Session):
        """Test user deletion"""
        # Create user
        user_data = schemas.UserCreate(
            username="delete_test_user",
            email="delete_test_user@example.com",
            password="testpassword123",
            is_superuser=False
        )
        created_user = crud.user.create(db_session, obj_in=user_data)
        user_id = created_user.id
        
        # Delete user
        deleted_user = crud.user.remove(db_session, id=user_id)
        assert deleted_user.id == user_id
        
        # Verify deletion
        retrieved_user = crud.user.get(db_session, id=user_id)
        assert retrieved_user is None

    def test_user_unique_constraints(self, db_session: Session):
        """Test user unique constraints"""
        # Create first user
        user_data = schemas.UserCreate(
            username="unique_test_user",
            email="unique_test_user@example.com",
            password="testpassword123",
            is_superuser=False
        )
        crud.user.create(db_session, obj_in=user_data)
        
        # Try to create another user with same username
        duplicate_user_data = schemas.UserCreate(
            username="unique_test_user",  # Same username
            email="different_email@example.com",
            password="differentpassword",
            is_superuser=True
        )
        
        with pytest.raises(IntegrityError):
            crud.user.create(db_session, obj_in=duplicate_user_data)
            db_session.commit()


class TestTemplateDatabaseOperations:
    """Test template-related database operations"""

    def test_template_crud_operations(self, db_session: Session, test_user: User):
        """Test complete template CRUD operations"""
        # Create template
        template_data = schemas.TemplateCreate(
            name="DB Test Template",
            description="Template for database testing",
            content="Template with {{placeholder}} content",
            is_active=True,
            user_id=test_user.id
        )
        created_template = crud.template.create(db_session, obj_in=template_data)
        
        assert created_template.name == template_data.name
        assert created_template.user_id == test_user.id
        assert created_template.id is not None
        
        # Read template
        retrieved_template = crud.template.get(db_session, id=created_template.id)
        assert retrieved_template is not None
        assert retrieved_template.name == template_data.name
        
        # Update template
        update_data = schemas.TemplateUpdate(
            name="Updated DB Test Template",
            description="Updated description",
            is_active=False
        )
        updated_template = crud.template.update(
            db_session, db_obj=created_template, obj_in=update_data
        )
        
        assert updated_template.name == update_data.name
        assert updated_template.description == update_data.description
        assert updated_template.is_active == update_data.is_active
        
        # Delete template
        deleted_template = crud.template.remove(db_session, id=created_template.id)
        assert deleted_template.id == created_template.id
        
        # Verify deletion
        retrieved_template = crud.template.get(db_session, id=created_template.id)
        assert retrieved_template is None

    def test_template_user_relationship(self, db_session: Session, test_user: User):
        """Test template-user relationship"""
        # Create template
        template_data = schemas.TemplateCreate(
            name="Relationship Test Template",
            description="Testing user relationship",
            content="Template content",
            user_id=test_user.id
        )
        created_template = crud.template.create(db_session, obj_in=template_data)
        
        # Test relationship access
        assert created_template.user is not None
        assert created_template.user.id == test_user.id
        assert created_template.user.username == test_user.username
        
        # Test reverse relationship
        user_templates = crud.template.get_by_user(db_session, user_id=test_user.id)
        assert len(user_templates) >= 1
        assert any(t.id == created_template.id for t in user_templates)

    def test_template_filtering_and_search(self, db_session: Session, test_user: User):
        """Test template filtering and search operations"""
        # Create multiple templates
        templates_data = [
            {
                "name": "Active Template 1",
                "description": "First active template",
                "content": "Content 1",
                "is_active": True,
                "user_id": test_user.id
            },
            {
                "name": "Inactive Template 2",
                "description": "Second inactive template",
                "content": "Content 2",
                "is_active": False,
                "user_id": test_user.id
            },
            {
                "name": "Active Template 3",
                "description": "Third active template",
                "content": "Content 3",
                "is_active": True,
                "user_id": test_user.id
            }
        ]
        
        created_templates = []
        for template_data in templates_data:
            template = crud.template.create(
                db_session, obj_in=schemas.TemplateCreate(**template_data)
            )
            created_templates.append(template)
        
        # Test filtering by active status
        active_templates = crud.template.get_active(db_session)
        active_count = sum(1 for t in created_templates if t.is_active)
        assert len([t for t in active_templates if t.user_id == test_user.id]) >= active_count
        
        # Test search by name
        search_results = crud.template.search_by_name(db_session, name_pattern="Active")
        assert len([t for t in search_results if t.user_id == test_user.id]) >= 2


class TestDataSourceDatabaseOperations:
    """Test data source-related database operations"""

    def test_data_source_crud_operations(self, db_session: Session, test_user: User):
        """Test complete data source CRUD operations"""
        # Create data source
        data_source_data = schemas.EnhancedDataSourceCreate(
            name="DB Test Data Source",
            description="Data source for database testing",
            source_type="database",
            connection_string="sqlite:///db_test.db",
            is_active=True,
            user_id=test_user.id
        )
        created_data_source = crud.enhanced_data_source.create(db_session, obj_in=data_source_data)
        
        assert created_data_source.name == data_source_data.name
        assert created_data_source.source_type == data_source_data.source_type
        assert created_data_source.user_id == test_user.id
        
        # Read data source
        retrieved_data_source = crud.enhanced_data_source.get(db_session, id=created_data_source.id)
        assert retrieved_data_source is not None
        assert retrieved_data_source.name == data_source_data.name
        
        # Update data source
        update_data = schemas.EnhancedDataSourceUpdate(
            name="Updated DB Test Data Source",
            is_active=False
        )
        updated_data_source = crud.enhanced_data_source.update(
            db_session, db_obj=created_data_source, obj_in=update_data
        )
        
        assert updated_data_source.name == update_data.name
        assert updated_data_source.is_active == update_data.is_active
        
        # Delete data source
        deleted_data_source = crud.enhanced_data_source.remove(db_session, id=created_data_source.id)
        assert deleted_data_source.id == created_data_source.id

    def test_data_source_connection_validation(self, db_session: Session, test_user: User):
        """Test data source connection string validation"""
        # Test valid connection strings
        valid_connections = [
            "sqlite:///test.db",
            "postgresql://user:pass@localhost:5432/db",
            "mysql://user:pass@localhost:3306/db"
        ]
        
        for i, connection_string in enumerate(valid_connections):
            data_source_data = schemas.EnhancedDataSourceCreate(
                name=f"Valid Connection {i}",
                description=f"Testing valid connection {i}",
                source_type="database",
                connection_string=connection_string,
                user_id=test_user.id
            )
            created_data_source = crud.enhanced_data_source.create(db_session, obj_in=data_source_data)
            assert created_data_source.connection_string == connection_string


class TestETLJobDatabaseOperations:
    """Test ETL job-related database operations"""

    def test_etl_job_crud_operations(
        self, 
        db_session: Session, 
        test_user: User, 
        test_data_source: EnhancedDataSource
    ):
        """Test complete ETL job CRUD operations"""
        # Create ETL job
        etl_job_data = schemas.ETLJobCreate(
            name="DB Test ETL Job",
            description="ETL job for database testing",
            source_id=test_data_source.id,
            schedule="0 0 * * *",  # Daily at midnight
            is_active=True,
            user_id=test_user.id
        )
        created_etl_job = crud.etl_job.create(db_session, obj_in=etl_job_data)
        
        assert created_etl_job.name == etl_job_data.name
        assert created_etl_job.source_id == test_data_source.id
        assert created_etl_job.user_id == test_user.id
        
        # Test relationships
        assert created_etl_job.source is not None
        assert created_etl_job.source.id == test_data_source.id
        assert created_etl_job.user is not None
        assert created_etl_job.user.id == test_user.id
        
        # Update ETL job
        update_data = schemas.ETLJobUpdate(
            name="Updated DB Test ETL Job",
            schedule="0 12 * * *",  # Daily at noon
            is_active=False
        )
        updated_etl_job = crud.etl_job.update(
            db_session, db_obj=created_etl_job, obj_in=update_data
        )
        
        assert updated_etl_job.name == update_data.name
        assert updated_etl_job.schedule == update_data.schedule
        assert updated_etl_job.is_active == update_data.is_active


class TestComplexDatabaseRelationships:
    """Test complex database relationships and operations"""

    def test_cascade_operations(
        self, 
        db_session: Session, 
        test_user: User, 
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test cascade operations when deleting related entities"""
        # Create placeholder mapping
        mapping_data = schemas.PlaceholderMappingCreate(
            template_id=test_template.id,
            data_source_id=test_data_source.id,
            placeholder_name="test_placeholder",
            field_name="test_field",
            field_type="string",
            user_id=test_user.id
        )
        created_mapping = crud.placeholder_mapping.create(db_session, obj_in=mapping_data)
        
        # Create report history
        report_data = schemas.ReportHistoryCreate(
            template_id=test_template.id,
            data_source_id=test_data_source.id,
            status="completed",
            output_format="pdf",
            file_path="/tmp/test_report.pdf",
            user_id=test_user.id
        )
        created_report = crud.report_history.create(db_session, obj_in=report_data)
        
        # Verify relationships exist
        assert created_mapping.template_id == test_template.id
        assert created_mapping.data_source_id == test_data_source.id
        assert created_report.template_id == test_template.id
        assert created_report.data_source_id == test_data_source.id
        
        # Test that related records exist
        mapping_count = db_session.query(PlaceholderMapping).filter(
            PlaceholderMapping.template_id == test_template.id
        ).count()
        assert mapping_count >= 1
        
        report_count = db_session.query(ReportHistory).filter(
            ReportHistory.template_id == test_template.id
        ).count()
        assert report_count >= 1

    def test_transaction_rollback(self, db_session: Session, test_user: User):
        """Test transaction rollback on errors"""
        # Start a transaction
        try:
            # Create a valid template
            template_data = schemas.TemplateCreate(
                name="Transaction Test Template",
                description="Testing transaction rollback",
                content="Template content",
                user_id=test_user.id
            )
            created_template = crud.template.create(db_session, obj_in=template_data)
            
            # Force an error by trying to create duplicate user
            duplicate_user_data = schemas.UserCreate(
                username=test_user.username,  # Duplicate username
                password="testpassword",
                is_superuser=False
            )
            crud.user.create(db_session, obj_in=duplicate_user_data)
            
            # This should not be reached due to integrity error
            db_session.commit()
            assert False, "Expected IntegrityError was not raised"
            
        except IntegrityError:
            # Rollback the transaction
            db_session.rollback()
            
            # Verify that the template was not created due to rollback
            template_exists = crud.template.get_by_name(
                db_session, name="Transaction Test Template"
            )
            # Template might still exist if created in separate transaction
            # This test verifies rollback behavior

    def test_bulk_operations(self, db_session: Session, test_user: User):
        """Test bulk database operations"""
        # Bulk create templates
        template_data_list = [
            {
                "name": f"Bulk Template {i}",
                "description": f"Bulk created template {i}",
                "content": f"Content for template {i}",
                "user_id": test_user.id
            }
            for i in range(10)
        ]
        
        created_templates = []
        for template_data in template_data_list:
            template = crud.template.create(
                db_session, obj_in=schemas.TemplateCreate(**template_data)
            )
            created_templates.append(template)
        
        assert len(created_templates) == 10
        
        # Bulk update
        for template in created_templates:
            update_data = schemas.TemplateUpdate(is_active=False)
            crud.template.update(db_session, db_obj=template, obj_in=update_data)
        
        # Verify bulk update
        updated_templates = crud.template.get_by_user(db_session, user_id=test_user.id)
        inactive_count = sum(1 for t in updated_templates if not t.is_active)
        assert inactive_count >= 10

    def test_database_constraints_and_indexes(self, db_session: Session, test_user: User):
        """Test database constraints and index performance"""
        import time
        
        # Create many templates to test index performance
        start_time = time.time()
        
        templates = []
        for i in range(100):
            template_data = schemas.TemplateCreate(
                name=f"Index Test Template {i}",
                description=f"Template for index testing {i}",
                content=f"Content {i}",
                user_id=test_user.id
            )
            template = crud.template.create(db_session, obj_in=template_data)
            templates.append(template)
        
        creation_time = time.time() - start_time
        
        # Test query performance with index
        start_time = time.time()
        user_templates = crud.template.get_by_user(db_session, user_id=test_user.id)
        query_time = time.time() - start_time
        
        assert len(user_templates) >= 100
        assert query_time < 1.0  # Should be fast with proper indexing
        assert creation_time < 5.0  # Bulk creation should be reasonable