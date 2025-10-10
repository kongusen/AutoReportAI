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
    优化的数据库依赖，带连接重试机制和健康检查
    """
    import time
    from sqlalchemy import text
    from sqlalchemy.exc import DisconnectionError, TimeoutError as SQLTimeoutError
    
    db = None
    max_retries = 3
    retry_delay = 1.0  # 重试延迟(秒)
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            
            # 连接健康检查，使用快速查询
            db.execute(text("SELECT 1"))
            
            logger.debug(f"数据库连接成功 (尝试 {attempt + 1}/{max_retries})")
            yield db
            break  # 成功后退出重试循环
            
        except (DisconnectionError, SQLTimeoutError) as e:
            # 连接或超时错误，可以重试
            logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if db:
                try:
                    db.rollback()
                    db.close()
                except:
                    pass
                db = None
            
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # 指数退避
                continue
            else:
                # 最后一次尝试失败
                logger.error(f"数据库连接在 {max_retries} 次尝试后仍然失败")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection failed after retries"
                )
                
        except SQLAlchemyError as e:
            # 其他SQL错误，通常不需要重试
            logger.error(f"数据库SQL错误: {e}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database operation failed"
            )
            
        except HTTPException:
            # 重新抛出HTTP异常（如认证错误）
            raise
            
        except Exception as e:
            logger.error(f"意外的数据库错误: {e}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected database error"
            )
        finally:
            if db:
                try:
                    db.close()
                except:
                    pass


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


# React Agent系统集成服务
def get_react_agent_llm_service(db: Session = Depends(get_db), user = Depends(get_current_user)):
    """获取React Agent LLM服务依赖"""
    try:
        from app.services.infrastructure.llm.simple_model_selector import SimpleModelSelector
        user_id = str(user.id) if user else None
        return SimpleModelSelector()
    except Exception as e:
        logger.error(f"Failed to create IntelligentLLMSelector: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="React Agent LLM service unavailable"
        )


def get_workflow_orchestration_agent(db: Session = Depends(get_db), user = Depends(get_current_user)):
    """获取工作流编排代理依赖（统一到新Agent适配器）"""
    try:
        from app.services.application.agents.new_workflow_orchestration_agent import WorkflowOrchestrationAgent
        user_id = str(user.id) if user else 'system'
        return WorkflowOrchestrationAgent(user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to create WorkflowOrchestrationAgent: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow orchestration agent unavailable"
        )


# React Agent服务依赖 - 统一接口
def get_ai_service(db: Session = Depends(get_db), user = Depends(get_current_user)):
    """获取React Agent AI服务依赖"""
    return get_react_agent_llm_service(db, user)


def get_agents_executor():
    """Get LLM orchestration service as executor dependency"""
    try:
        from app.services.application.llm import get_llm_orchestration_service
        return get_llm_orchestration_service()
    except Exception as e:
        logger.error(f"Failed to create LLM orchestration service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM orchestration service unavailable"
        )


def get_context_builder():
    """Get agents context builder dependency"""
    try:
        from app.services.infrastructure.agents.context import AgentContextBuilder
        return AgentContextBuilder()
    except Exception as e:
        logger.error(f"Failed to create ContextBuilder: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Context builder service unavailable"
        )


def get_content_generation_service():
    """Get content generation service (using LLM orchestration)"""
    try:
        from app.services.application.llm import get_llm_orchestration_service
        return get_llm_orchestration_service()
    except Exception as e:
        logger.error(f"Failed to create ContentGenerationService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content generation service unavailable"
        )


def get_visualization_service():
    """Get visualization service (using LLM orchestration)"""
    try:
        from app.services.application.llm import get_llm_orchestration_service
        return get_llm_orchestration_service()
    except Exception as e:
        logger.error(f"Failed to create VisualizationService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Visualization service unavailable"
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
    """Get task manager dependency - using new DDD task system"""
    try:
        # 使用新的DDD任务管理器
        from app.services.application.task_management.ddd_task_examples import DDDTaskManager
        return DDDTaskManager()
    except Exception as e:
        logger.error(f"Failed to create DDDTaskManager: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task manager service unavailable"
        )


def get_status_tracker(db: Session = Depends(get_db)):
    """Get status tracker dependency - using Celery task status"""
    try:
        # 使用Celery的任务状态追踪
        from app.services.infrastructure.task_queue.celery_config import celery_app
        
        class CeleryStatusTracker:
            def __init__(self):
                self.celery_app = celery_app
                
            def get_task_status(self, task_id):
                result = self.celery_app.AsyncResult(task_id)
                return {
                    'task_id': task_id,
                    'status': result.status,
                    'result': result.result if result.ready() else None
                }
        
        return CeleryStatusTracker()
    except Exception as e:
        logger.error(f"Failed to create CeleryStatusTracker: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Status tracker service unavailable"
        )


def get_task_scheduler(db: Session = Depends(get_db)):
    """Get task scheduler dependency"""
    try:
        from app.services.application.task_management.core.scheduler import TaskScheduler
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
        from app.services.application.task_management.execution.agent_executor import AgentExecutor
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
        from app.services.application.task_management.execution.fallback import FallbackHandler
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
        try:
            db.execute("SELECT 1")
        finally:
            db.close()
    except Exception as e:
        dependencies["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    return dependencies
