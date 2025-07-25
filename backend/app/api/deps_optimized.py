"""
优化的依赖注入模块
集成新的优化架构和原有功能
"""

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

# 导入优化的组件
from app.services.optimized import services
from app.models.optimized.user import User as OptimizedUser
from app.crud.optimized.crud_user import crud_user as optimized_crud_user

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/access-token"
)


def get_db() -> Generator:
    """
    优化的数据库依赖，支持连接健康检查和错误处理
    """
    db = None
    try:
        db = SessionLocal()
        # 测试连接健康状态
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
        # 重新抛出HTTP异常（如认证错误）不做修改
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
    """获取当前用户，兼容原有和优化的用户系统"""
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
    
    # 使用原有的CRUD方法获取用户
    user = crud.user.get_by_username(db, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 强制user.id为UUID类型
    from uuid import UUID
    if isinstance(user.id, str):
        user.id = UUID(user.id)
    return user


def get_current_user_optimized(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> OptimizedUser:
    """获取当前用户（优化版本）"""
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
    
    # 使用优化的CRUD方法
    user = optimized_crud_user.get_by_username(db, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_user_optimized(
    current_user: OptimizedUser = Depends(get_current_user_optimized),
) -> OptimizedUser:
    """获取当前活跃用户（优化版本）"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """获取当前超级用户"""
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_active_superuser_optimized(
    current_user: OptimizedUser = Depends(get_current_active_user_optimized),
) -> OptimizedUser:
    """获取当前超级用户（优化版本）"""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


# ============================================================================
# 优化服务依赖
# ============================================================================

def get_data_source_service():
    """获取数据源服务"""
    return services.data_source


def get_report_service():
    """获取报告服务"""
    return services.report


def get_service_manager():
    """获取服务管理器"""
    return services


# ============================================================================
# 原有服务依赖（保持兼容性）
# ============================================================================

def get_learning_service(db: Session = Depends(get_db)):
    """Get learning service dependency"""
    from app.services.learning_service import LearningService
    return LearningService(db)


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


# ============================================================================
# 健康检查和监控
# ============================================================================

def get_system_health(db: Session = Depends(get_db)) -> dict:
    """获取系统健康状态"""
    health_status = {
        "database": "healthy",
        "services": {},
        "overall": "healthy"
    }
    
    try:
        # 检查数据库连接
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # 检查优化服务
        try:
            services.data_source
            health_status["services"]["data_source"] = "healthy"
        except Exception as e:
            health_status["services"]["data_source"] = f"unhealthy: {str(e)}"
            health_status["overall"] = "degraded"
        
        try:
            services.report
            health_status["services"]["report"] = "healthy"
        except Exception as e:
            health_status["services"]["report"] = f"unhealthy: {str(e)}"
            health_status["overall"] = "degraded"
        
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
        health_status["overall"] = "unhealthy"
    
    return health_status


def check_service_dependencies() -> dict:
    """检查服务依赖"""
    dependencies = {
        "aiohttp": False,
        "anthropic": False,
        "google_ai": False,
        "sentence_transformers": False
    }
    
    try:
        import aiohttp
        dependencies["aiohttp"] = True
    except ImportError:
        pass
    
    try:
        import anthropic
        dependencies["anthropic"] = True
    except ImportError:
        pass
    
    try:
        import google.generativeai
        dependencies["google_ai"] = True
    except ImportError:
        pass
    
    try:
        import sentence_transformers
        dependencies["sentence_transformers"] = True
    except ImportError:
        pass
    
    return dependencies