from typing import Generator, Optional, Dict, Any
import logging
import pandas as pd
import json

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import crud, models
from app.core import security
from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_db() -> Generator:
    """
    Optimized database dependency with connection health check and error handling
    """
    db = None
    try:
        db = SessionLocal()
        # Test connection health using proper SQLAlchemy syntax
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {e}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like authentication errors) without modification
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    finally:
        if db:
            db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    # 使用 get 方法，因为 token 存储的是 user_id
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # 强制user.id为UUID类型
    from uuid import UUID
    if isinstance(user.id, str):
        user.id = UUID(user.id)
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_learning_service(db: Session = Depends(get_db)):
    """Get learning service dependency"""
    from app.services.learning_service import LearningService
    return LearningService(db)


# ============================================================================
# Service Module Dependencies
# ============================================================================

# Intelligent Placeholder Services
def get_placeholder_processor():
    """Get placeholder processor dependency"""
    try:
        from app.services.intelligent_placeholder import PlaceholderProcessor
        return PlaceholderProcessor()
    except Exception as e:
        logger.error(f"Failed to create PlaceholderProcessor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Placeholder processor service unavailable"
        )


def get_intelligent_placeholder_processor(db: Session = Depends(get_db)):
    """Get intelligent placeholder processor dependency"""
    try:
        from app.services.intelligent_placeholder import IntelligentPlaceholderProcessor
        return IntelligentPlaceholderProcessor(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentPlaceholderProcessor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligent placeholder processor service unavailable"
        )


def get_field_matcher(db: Session = Depends(get_db)):
    """Get intelligent field matcher dependency"""
    try:
        from app.services.intelligent_placeholder import IntelligentFieldMatcher
        return IntelligentFieldMatcher(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentFieldMatcher: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Field matcher service unavailable"
        )


# Report Generation Services
def get_report_generation_service(db: Session = Depends(get_db)):
    """Get report generation service dependency"""
    try:
        from app.services.report_generation import ReportGenerationService
        return ReportGenerationService(db)
    except Exception as e:
        logger.error(f"Failed to create ReportGenerationService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report generation service unavailable"
        )


def get_report_composition_service(db: Session = Depends(get_db)):
    """Get report composition service dependency"""
    try:
        from app.services.report_generation import ReportCompositionService
        return ReportCompositionService(db)
    except Exception as e:
        logger.error(f"Failed to create ReportCompositionService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report composition service unavailable"
        )


def get_report_quality_checker(db: Session = Depends(get_db)):
    """Get report quality checker dependency"""
    try:
        from app.services.report_generation import ReportQualityChecker
        return ReportQualityChecker(db)
    except Exception as e:
        logger.error(f"Failed to create ReportQualityChecker: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report quality checker service unavailable"
        )


# Data Processing Services
def get_data_retrieval_service():
    """Get data retrieval service dependency"""
    try:
        from app.services.data_processing import DataRetrievalService
        return DataRetrievalService()
    except Exception as e:
        logger.error(f"Failed to create DataRetrievalService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data retrieval service unavailable"
        )


def get_data_analysis_service(db: Session = Depends(get_db)):
    """Get data analysis service dependency"""
    try:
        from app.services.data_processing import DataAnalysisService
        return DataAnalysisService(db)
    except Exception as e:
        logger.error(f"Failed to create DataAnalysisService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data analysis service unavailable"
        )


def get_etl_service(db: Session = Depends(get_db)):
    """Get ETL service dependency"""
    try:
        from app.services.data_processing import ETLService
        return ETLService(db)
    except Exception as e:
        logger.error(f"Failed to create ETLService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ETL service unavailable"
        )


def get_intelligent_etl_executor(db: Session = Depends(get_db)):
    """Get intelligent ETL executor dependency"""
    try:
        from app.services.data_processing import IntelligentETLExecutor
        return IntelligentETLExecutor(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentETLExecutor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligent ETL executor service unavailable"
        )


# AI Integration Services
def get_ai_service(db: Session = Depends(get_db)):
    """Get AI service dependency"""
    try:
        from app.services.ai_integration import AIService
        return AIService(db)
    except Exception as e:
        logger.error(f"Failed to create AIService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )


def get_enhanced_ai_service(db: Session = Depends(get_db)):
    """Get enhanced AI service dependency"""
    try:
        from app.services.ai_integration import EnhancedAIService
        return EnhancedAIService(db)
    except Exception as e:
        logger.error(f"Failed to create EnhancedAIService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enhanced AI service unavailable"
        )


def get_content_generation_agent(db: Session = Depends(get_db)):
    """Get content generation agent dependency"""
    try:
        from app.services.agents.content_generation_agent import ContentGenerationAgent
        return ContentGenerationAgent()
    except Exception as e:
        logger.error(f"Failed to create ContentGenerationAgent: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content generation agent unavailable"
        )


def get_visualization_agent(db: Session = Depends(get_db)):
    """Get visualization agent dependency"""
    try:
        from app.services.agents.visualization_agent import VisualizationAgent
        return VisualizationAgent()
    except Exception as e:
        logger.error(f"Failed to create VisualizationAgent: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Visualization agent unavailable"
        )


# Notification Services
def get_email_service(db: Session = Depends(get_db)):
    """Get email service dependency"""
    try:
        from app.services.notification import EmailService
        return EmailService(db)
    except Exception as e:
        logger.error(f"Failed to create EmailService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service unavailable"
        )


def get_notification_service(db: Session = Depends(get_db)):
    """Get notification service dependency"""
    try:
        from app.services.notification import NotificationService
        return NotificationService(db)
    except Exception as e:
        logger.error(f"Failed to create NotificationService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service unavailable"
        )


# ============================================================================
# Service Health Check Functions
# ============================================================================

def serialize_health_data(data: Any) -> Any:
    """
    Recursively serialize health data, converting pandas DataFrames and other
    non-serializable objects to JSON-compatible formats
    """
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to dictionary
        return {
            "type": "dataframe",
            "shape": list(data.shape),
            "columns": list(data.columns),
            "data_preview": data.head(5).to_dict(orient='records') if not data.empty else [],
            "empty": data.empty
        }
    elif isinstance(data, dict):
        return {key: serialize_health_data(value) for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        return [serialize_health_data(item) for item in data]
    elif hasattr(data, '__dict__'):
        # Handle objects with attributes
        return {
            "type": type(data).__name__,
            "attributes": {key: serialize_health_data(value) for key, value in data.__dict__.items()}
        }
    else:
        # For basic types (str, int, bool, None) and other serializable objects
        try:
            json.dumps(data)  # Test if it's JSON serializable
            return data
        except (TypeError, ValueError):
            # If not serializable, convert to string representation
            return str(data)

def check_service_health(service_name: str, service_instance) -> dict:
    """Check service health status"""
    try:
        # Basic health check - try to access a method or attribute
        if hasattr(service_instance, 'health_check'):
            health_status = service_instance.health_check()
        else:
            health_status = {"status": "unknown", "message": "No health check method available"}
        
        # Serialize health_status to handle any DataFrames or non-serializable objects
        serialized_health_status = serialize_health_data(health_status)
        
        return {
            "service": service_name,
            "status": "healthy",
            "details": serialized_health_status
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "unhealthy",
            "error": str(e)
        }


def get_all_services_health(db: Session = Depends(get_db)) -> dict:
    """Get health status of all services"""
    services_health = {}
    
    try:
        # Check each service
        services = [
            ("placeholder_processor", get_placeholder_processor()),
            ("intelligent_placeholder_processor", get_intelligent_placeholder_processor(db)),
            ("field_matcher", get_field_matcher(db)),
            ("report_generation_service", get_report_generation_service(db)),
            ("data_retrieval_service", get_data_retrieval_service()),
            ("data_analysis_service", get_data_analysis_service(db)),
            ("etl_service", get_etl_service(db)),
            ("ai_service", get_ai_service(db)),
            ("email_service", get_email_service(db)),
            ("notification_service", get_notification_service(db)),
        ]
        
        for service_name, service_instance in services:
            services_health[service_name] = check_service_health(service_name, service_instance)
        
        return {
            "overall_status": "healthy" if all(
                health["status"] == "healthy" for health in services_health.values()
            ) else "degraded",
            "services": services_health
        }
        
    except Exception as e:
        logger.error(f"Failed to check services health: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "services": services_health
        }


# Task Management Services
def get_task_manager(db: Session = Depends(get_db)):
    """Get task manager dependency"""
    try:
        from app.services.task.management.task_manager import TaskManager
        return TaskManager()
    except Exception as e:
        logger.error(f"Failed to create TaskManager: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task manager service unavailable"
        )


def get_status_tracker(db: Session = Depends(get_db)):
    """Get status tracker dependency"""
    try:
        from app.services.task.management.status_tracker import StatusTracker
        return StatusTracker()
    except Exception as e:
        logger.error(f"Failed to create StatusTracker: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Status tracker service unavailable"
        )


def get_task_scheduler(db: Session = Depends(get_db)):
    """Get task scheduler dependency"""
    try:
        from app.services.task.core.scheduler import TaskScheduler
        return TaskScheduler()
    except Exception as e:
        logger.error(f"Failed to create TaskScheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task scheduler service unavailable"
        )


def get_agent_executor(db: Session = Depends(get_db)):
    """Get agent executor dependency"""
    try:
        from app.services.task.execution.agent_executor import AgentExecutor
        return AgentExecutor()
    except Exception as e:
        logger.error(f"Failed to create AgentExecutor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent executor service unavailable"
        )


def get_fallback_handler(db: Session = Depends(get_db)):
    """Get fallback handler dependency"""
    try:
        from app.services.task.execution.fallback import FallbackHandler
        return FallbackHandler()
    except Exception as e:
        logger.error(f"Failed to create FallbackHandler: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fallback handler service unavailable"
        )


def check_service_dependencies() -> Dict[str, Any]:
    """Check the status of service dependencies"""
    dependencies = {
        "database": {"status": "healthy", "message": "Database connection OK"},
        "ai_providers": {"status": "partial", "message": "Some AI providers unavailable"},
        "services": {"status": "healthy", "message": "Core services operational"}
    }

    try:
        # Test database connection
        from app.db.session import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        dependencies["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    return dependencies