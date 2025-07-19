from typing import Generator, Optional
import logging

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

# Service imports
from app.services.intelligent_placeholder import (
    IntelligentPlaceholderProcessor,
    IntelligentFieldMatcher,
    PlaceholderProcessor
)
from app.services.report_generation import (
    ReportGenerationService,
    ReportCompositionService,
    ReportQualityChecker
)
from app.services.data_processing import (
    DataRetrievalService,
    DataAnalysisService,
    ETLService,
    IntelligentETLExecutor
)
from app.services.ai_integration import (
    AIService,
    EnhancedAIService,
    ContentGenerator,
    ChartGenerator
)
from app.services.notification import (
    EmailService,
    NotificationService
)

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/access-token"
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
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    # 使用 get_by_username 而不是 get，因为 token 存储的是 username
    user = crud.user.get_by_username(db, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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
def get_placeholder_processor() -> PlaceholderProcessor:
    """Get placeholder processor dependency"""
    try:
        return PlaceholderProcessor()
    except Exception as e:
        logger.error(f"Failed to create PlaceholderProcessor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Placeholder processor service unavailable"
        )


def get_intelligent_placeholder_processor(db: Session = Depends(get_db)) -> IntelligentPlaceholderProcessor:
    """Get intelligent placeholder processor dependency"""
    try:
        return IntelligentPlaceholderProcessor(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentPlaceholderProcessor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligent placeholder processor service unavailable"
        )


def get_field_matcher(db: Session = Depends(get_db)) -> IntelligentFieldMatcher:
    """Get intelligent field matcher dependency"""
    try:
        return IntelligentFieldMatcher(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentFieldMatcher: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Field matcher service unavailable"
        )


# Report Generation Services
def get_report_generation_service(db: Session = Depends(get_db)) -> ReportGenerationService:
    """Get report generation service dependency"""
    try:
        return ReportGenerationService(db)
    except Exception as e:
        logger.error(f"Failed to create ReportGenerationService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report generation service unavailable"
        )


def get_report_composition_service(db: Session = Depends(get_db)) -> ReportCompositionService:
    """Get report composition service dependency"""
    try:
        return ReportCompositionService(db)
    except Exception as e:
        logger.error(f"Failed to create ReportCompositionService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report composition service unavailable"
        )


def get_report_quality_checker(db: Session = Depends(get_db)) -> ReportQualityChecker:
    """Get report quality checker dependency"""
    try:
        return ReportQualityChecker(db)
    except Exception as e:
        logger.error(f"Failed to create ReportQualityChecker: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report quality checker service unavailable"
        )


# Data Processing Services
def get_data_retrieval_service() -> DataRetrievalService:
    """Get data retrieval service dependency"""
    try:
        return DataRetrievalService()
    except Exception as e:
        logger.error(f"Failed to create DataRetrievalService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data retrieval service unavailable"
        )


def get_data_analysis_service(db: Session = Depends(get_db)) -> DataAnalysisService:
    """Get data analysis service dependency"""
    try:
        return DataAnalysisService(db)
    except Exception as e:
        logger.error(f"Failed to create DataAnalysisService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data analysis service unavailable"
        )


def get_etl_service(db: Session = Depends(get_db)) -> ETLService:
    """Get ETL service dependency"""
    try:
        return ETLService(db)
    except Exception as e:
        logger.error(f"Failed to create ETLService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ETL service unavailable"
        )


def get_intelligent_etl_executor(db: Session = Depends(get_db)) -> IntelligentETLExecutor:
    """Get intelligent ETL executor dependency"""
    try:
        return IntelligentETLExecutor(db)
    except Exception as e:
        logger.error(f"Failed to create IntelligentETLExecutor: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligent ETL executor service unavailable"
        )


# AI Integration Services
def get_ai_service(db: Session = Depends(get_db)) -> AIService:
    """Get AI service dependency"""
    try:
        return AIService(db)
    except Exception as e:
        logger.error(f"Failed to create AIService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )


def get_enhanced_ai_service(db: Session = Depends(get_db)) -> EnhancedAIService:
    """Get enhanced AI service dependency"""
    try:
        return EnhancedAIService(db)
    except Exception as e:
        logger.error(f"Failed to create EnhancedAIService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enhanced AI service unavailable"
        )


def get_content_generator(db: Session = Depends(get_db)) -> ContentGenerator:
    """Get content generator dependency"""
    try:
        return ContentGenerator(db)
    except Exception as e:
        logger.error(f"Failed to create ContentGenerator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content generator service unavailable"
        )


def get_chart_generator(db: Session = Depends(get_db)) -> ChartGenerator:
    """Get chart generator dependency"""
    try:
        return ChartGenerator(db)
    except Exception as e:
        logger.error(f"Failed to create ChartGenerator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chart generator service unavailable"
        )


# Notification Services
def get_email_service(db: Session = Depends(get_db)) -> EmailService:
    """Get email service dependency"""
    try:
        return EmailService(db)
    except Exception as e:
        logger.error(f"Failed to create EmailService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service unavailable"
        )


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    """Get notification service dependency"""
    try:
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

def check_service_health(service_name: str, service_instance) -> dict:
    """
    Generic service health check function
    """
    try:
        # Check if service has a health_check method
        if hasattr(service_instance, 'health_check'):
            return service_instance.health_check()
        else:
            # Basic health check - just verify the service can be instantiated
            return {
                "status": "healthy",
                "service": service_name,
                "message": "Service is available"
            }
    except Exception as e:
        logger.error(f"Health check failed for {service_name}: {e}")
        return {
            "status": "unhealthy",
            "service": service_name,
            "error": str(e)
        }


def get_all_services_health(db: Session = Depends(get_db)) -> dict:
    """
    Get health status of all services
    """
    health_status = {
        "overall_status": "healthy",
        "timestamp": None,
        "services": {}
    }
    
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()
    
    # Database health
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Service health checks
    services_to_check = [
        ("placeholder_processor", lambda: PlaceholderProcessor()),
        ("intelligent_placeholder", lambda: IntelligentPlaceholderProcessor(db)),
        ("report_generation", lambda: ReportGenerationService(db)),
        ("data_retrieval", lambda: DataRetrievalService()),
        ("ai_service", lambda: AIService(db)),
        ("email_service", lambda: EmailService(db)),
    ]
    
    for service_name, service_factory in services_to_check:
        try:
            service_instance = service_factory()
            health_status["services"][service_name] = check_service_health(
                service_name, service_instance
            )
            
            # Update overall status if any service is unhealthy
            if health_status["services"][service_name]["status"] != "healthy":
                health_status["overall_status"] = "degraded"
                
        except Exception as e:
            logger.error(f"Failed to check health for {service_name}: {e}")
            health_status["services"][service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
    
    return health_status