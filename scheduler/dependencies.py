"""
Dependency injection container for the scheduler.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.report_generation_service import ReportGenerationService
from app.services.email_service import EmailService
from app.services.etl_service import etl_service


class ServiceContainer:
    """
    A simple dependency injection container for managing service instances.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._services: Dict[str, Any] = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services."""
        self._services['report_generation'] = ReportGenerationService(self.db_session)
        self._services['email'] = EmailService()
        self._services['etl'] = etl_service
    
    def get_report_generation_service(self) -> ReportGenerationService:
        """Get the report generation service."""
        return self._services['report_generation']
    
    def get_email_service(self) -> EmailService:
        """Get the email service."""
        return self._services['email']
    
    def get_etl_service(self):
        """Get the ETL service."""
        return self._services['etl']
    
    def get_service(self, service_name: str) -> Any:
        """Get a service by name."""
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' not found")
        return self._services[service_name]


def create_service_container(db_session: Session) -> ServiceContainer:
    """
    Factory function to create a service container.
    """
    return ServiceContainer(db_session) 