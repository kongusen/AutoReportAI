"""
系统健康检查端点
提供数据库连接池、断路器、韧性管理等系统状态监控
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from app.api.deps import get_db
from app.db.session import get_db_health_status
from app.services.data.connectors.resilience_manager import get_resilience_manager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", summary="系统整体健康状态")
async def get_system_health() -> Dict[str, Any]:
    """获取系统整体健康状态"""
    try:
        # 数据库健康状态
        db_health = get_db_health_status()
        
        # 韧性管理器健康状态
        resilience_manager = get_resilience_manager()
        resilience_health = resilience_manager.get_health_report()
        
        # 基础系统信息
        system_info = {
            "environment": settings.ENVIRONMENT_TYPE,
            "debug_mode": settings.DEBUG,
            "database_url_type": "docker" if "db:" in settings.DATABASE_URL else "local",
            "connection_pool_config": {
                "pool_size": settings.DATABASE_URL,  # 显示配置源
                "environment_detected": settings.ENVIRONMENT_TYPE
            }
        }
        
        # 计算整体健康状态
        overall_status = "healthy"
        if db_health.get("status") != "healthy":
            overall_status = "unhealthy"
        elif resilience_health.get("overall_health") == "degraded":
            overall_status = "degraded"
        elif resilience_health.get("overall_health") == "unhealthy":
            overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": resilience_health.get("timestamp"),
            "components": {
                "database": db_health,
                "resilience": resilience_health,
                "system": system_info
            },
            "summary": {
                "total_circuit_breakers": resilience_health.get("total_circuit_breakers", 0),
                "open_circuit_breakers": resilience_health.get("open_circuit_breakers", 0),
                "database_pool_size": db_health.get("pool_size", 0),
                "database_checked_out": db_health.get("checked_out", 0),
                "database_overflow": db_health.get("overflow", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": None
        }


@router.get("/health/database", summary="数据库健康状态")
async def get_database_health() -> Dict[str, Any]:
    """获取数据库连接池详细健康状态"""
    try:
        db_health = get_db_health_status()
        
        # 添加连接池详细信息
        from app.db.session import engine
        pool_info = {
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin(),
            "pool_capacity": engine.pool.size() + engine.pool.overflow(),
            "utilization_rate": (engine.pool.checkedout() / (engine.pool.size() + engine.pool.overflow())) * 100 
                               if (engine.pool.size() + engine.pool.overflow()) > 0 else 0
        }
        
        db_health["pool_details"] = pool_info
        return db_health
        
    except Exception as e:
        logger.error(f"获取数据库健康状态失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/health/resilience", summary="韧性管理健康状态")
async def get_resilience_health() -> Dict[str, Any]:
    """获取韧性管理详细健康状态"""
    try:
        resilience_manager = get_resilience_manager()
        return resilience_manager.get_health_report()
        
    except Exception as e:
        logger.error(f"获取韧性健康状态失败: {e}")
        return {
            "overall_health": "unhealthy",
            "error": str(e)
        }


@router.get("/health/circuit-breakers", summary="断路器状态")
async def get_circuit_breakers_status() -> Dict[str, Any]:
    """获取所有断路器的详细状态"""
    try:
        resilience_manager = get_resilience_manager()
        health_report = resilience_manager.get_health_report()
        
        circuit_breakers = health_report.get("circuit_breakers", {})
        
        # 按状态分组
        status_groups = {
            "closed": [],
            "open": [],
            "half_open": []
        }
        
        for name, status in circuit_breakers.items():
            state = status.get("state", "unknown")
            if state in status_groups:
                status_groups[state].append({
                    "name": name,
                    "failure_count": status.get("failure_count", 0),
                    "success_count": status.get("success_count", 0),
                    "last_failure_time": status.get("last_failure_time"),
                    "config": status.get("config", {})
                })
        
        return {
            "total_circuit_breakers": len(circuit_breakers),
            "status_summary": {
                "closed": len(status_groups["closed"]),
                "open": len(status_groups["open"]),
                "half_open": len(status_groups["half_open"])
            },
            "circuit_breakers_by_status": status_groups,
            "timestamp": health_report.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"获取断路器状态失败: {e}")
        return {
            "error": str(e)
        }


@router.get("/health/connections", summary="连接监控状态")
async def get_connections_status() -> Dict[str, Any]:
    """获取所有连接的监控状态"""
    try:
        resilience_manager = get_resilience_manager()
        health_report = resilience_manager.get_health_report()
        
        connection_metrics = health_report.get("connection_metrics", {})
        
        # 按健康状态分组
        health_groups = {
            "healthy": [],
            "degraded": [],
            "unhealthy": [],
            "unknown": []
        }
        
        for name, metrics in connection_metrics.items():
            if isinstance(metrics, dict) and "current_health" in metrics:
                health_status = metrics.get("current_health", "unknown")
                if health_status in health_groups:
                    health_groups[health_status].append({
                        "name": name,
                        "total_requests": metrics.get("total_requests", 0),
                        "success_rate": metrics.get("success_rate", 0),
                        "average_response_time": metrics.get("average_response_time", 0),
                        "last_success_time": metrics.get("last_success_time"),
                        "last_failure_time": metrics.get("last_failure_time"),
                        "recent_failures_count": metrics.get("recent_failures_count", 0)
                    })
        
        return {
            "total_connections": len([m for m in connection_metrics.values() if isinstance(m, dict)]),
            "health_summary": {
                "healthy": len(health_groups["healthy"]),
                "degraded": len(health_groups["degraded"]),
                "unhealthy": len(health_groups["unhealthy"]),
                "unknown": len(health_groups["unknown"])
            },
            "connections_by_health": health_groups,
            "timestamp": health_report.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"获取连接状态失败: {e}")
        return {
            "error": str(e)
        }


@router.post("/health/circuit-breakers/{breaker_name}/reset", summary="重置断路器")
async def reset_circuit_breaker(breaker_name: str) -> Dict[str, Any]:
    """手动重置指定的断路器"""
    try:
        resilience_manager = get_resilience_manager()
        
        if breaker_name in resilience_manager.circuit_breakers:
            circuit_breaker = resilience_manager.circuit_breakers[breaker_name]
            
            # 重置断路器状态
            with circuit_breaker.lock:
                from app.services.data.connectors.resilience_manager import CircuitBreakerState
                circuit_breaker.state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
                circuit_breaker.success_count = 0
                circuit_breaker.last_failure_time = None
            
            logger.info(f"断路器 {breaker_name} 已手动重置")
            
            return {
                "success": True,
                "message": f"Circuit breaker {breaker_name} has been reset",
                "breaker_status": circuit_breaker.get_state()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker {breaker_name} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置断路器失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.get("/health/data-sources/{data_source_id}", summary="数据源健康状态")
async def get_data_source_health(data_source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取特定数据源的健康状态"""
    try:
        from app.models.data_source import DataSource
        from app.services.data.connectors.connector_factory import create_connector
        
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not data_source:
            raise HTTPException(status_code=404, detail="Data source not found")
        
        # 创建连接器并检查健康状态
        connector = create_connector(data_source)
        
        # 如果是Doris连接器，获取韧性健康状态
        if hasattr(connector, 'get_resilience_health_status'):
            await connector.connect()
            try:
                resilience_health = await connector.get_resilience_health_status()
                return resilience_health
            finally:
                await connector.disconnect()
        else:
            # 对于其他连接器，执行基础健康检查
            await connector.connect()
            try:
                test_result = await connector.test_connection()
                return {
                    "connector_type": type(connector).__name__,
                    "data_source_id": data_source_id,
                    "basic_connection": test_result,
                    "timestamp": None
                }
            finally:
                await connector.disconnect()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据源健康状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data source health: {str(e)}"
        )