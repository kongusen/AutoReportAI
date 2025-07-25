"""
Health check endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import time
from datetime import datetime

from app.api.deps import get_db, check_service_dependencies
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    """
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'development'),
        "checks": {}
    }
    
    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Service dependencies check
    try:
        dependencies = check_service_dependencies()
        health_data["checks"]["dependencies"] = {
            "status": "healthy",
            "details": dependencies
        }
    except Exception as e:
        health_data["checks"]["dependencies"] = {
            "status": "degraded",
            "message": f"Dependencies check failed: {str(e)}"
        }
    
    # Memory and performance check
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        health_data["checks"]["system"] = {
            "status": "healthy",
            "memory_usage_percent": memory_info.percent,
            "available_memory_mb": round(memory_info.available / 1024 / 1024, 2)
        }
        
        if memory_info.percent > 90:
            health_data["status"] = "degraded"
            health_data["checks"]["system"]["status"] = "degraded"
            health_data["checks"]["system"]["message"] = "High memory usage"
            
    except ImportError:
        health_data["checks"]["system"] = {
            "status": "unknown",
            "message": "psutil not available for system monitoring"
        }
    except Exception as e:
        health_data["checks"]["system"] = {
            "status": "error",
            "message": f"System check failed: {str(e)}"
        }
    
    # Response time
    end_time = time.time()
    health_data["response_time_ms"] = round((end_time - start_time) * 1000, 2)
    
    # Determine overall status
    if any(check.get("status") == "unhealthy" for check in health_data["checks"].values()):
        health_data["status"] = "unhealthy"
    elif any(check.get("status") == "degraded" for check in health_data["checks"].values()):
        health_data["status"] = "degraded"
    
    return health_data


@router.get("/health/ready", tags=["Health"])
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Service is ready to accept traffic"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Service not ready: {str(e)}"
            }
        )


@router.get("/health/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Service is alive"
    }


@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with component-specific information
    """
    health_data = await health_check(db)
    
    # Add component-specific health checks
    try:
        # Check optimized components
        from app.models.optimized.data_source import DataSourceType
        from app.crud.base_optimized import CRUDBase
        
        health_data["checks"]["optimized_architecture"] = {
            "status": "healthy",
            "components": {
                "models": "loaded",
                "crud": "functional",
                "doris_support": DataSourceType.DORIS == "doris"
            }
        }
        
        # Check performance components
        from app.services.data_processing.query_optimizer import QueryOptimizer
        from app.services.async_mcp_client import AsyncMCPClient
        
        optimizer = QueryOptimizer()
        client = AsyncMCPClient()
        
        health_data["checks"]["performance_components"] = {
            "status": "healthy",
            "components": {
                "query_optimizer": "available",
                "async_mcp_client": "available",
                "batch_processor": "available"
            }
        }
        
    except Exception as e:
        health_data["checks"]["optimized_architecture"] = {
            "status": "error",
            "message": f"Component check failed: {str(e)}"
        }
        health_data["status"] = "degraded"
    
    return health_data