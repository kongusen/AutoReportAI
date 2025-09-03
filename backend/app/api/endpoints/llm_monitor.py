"""
LLM访问监控API端点

提供LLM速度限制器的状态监控和管理接口
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.core.architecture import ApiResponse
from app.services.infrastructure.ai.llm.rate_limiter import (
    get_llm_rate_limiter, reset_llm_rate_limiter
)
from app.services.infrastructure.ai.service_pool import (
    get_ai_service_pool, reset_ai_service_pool
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=ApiResponse)
async def get_llm_rate_limiter_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取LLM速度限制器状态"""
    try:
        rate_limiter = get_llm_rate_limiter()
        status = rate_limiter.get_statistics()
        
        # 添加健康检查信息
        health = await rate_limiter.health_check()
        status['health'] = health
        
        return ApiResponse(
            success=True,
            data=status,
            message="LLM速度限制器状态获取成功"
        )
    except Exception as e:
        logger.error(f"获取LLM速度限制器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/ai-service-pool", response_model=ApiResponse)
async def get_ai_service_pool_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取AI服务连接池状态"""
    try:
        pool = get_ai_service_pool()
        pool_stats = pool.get_pool_stats()
        
        return ApiResponse(
            success=True,
            data=pool_stats,
            message="AI服务连接池状态获取成功"
        )
    except Exception as e:
        logger.error(f"获取AI服务连接池状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/reset-statistics", response_model=ApiResponse)
async def reset_llm_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重置LLM速度限制器统计信息"""
    try:
        rate_limiter = get_llm_rate_limiter()
        rate_limiter.reset_statistics()
        
        logger.info(f"用户 {current_user.username} 重置了LLM速度限制器统计信息")
        
        return ApiResponse(
            success=True,
            data={"reset_time": "now"},
            message="LLM统计信息重置成功"
        )
    except Exception as e:
        logger.error(f"重置LLM统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.post("/reset-rate-limiter", response_model=ApiResponse)
async def reset_rate_limiter_instance(
    max_concurrent: int = Query(1, description="最大并发请求数"),
    min_interval: float = Query(1.0, description="最小请求间隔(秒)"),
    timeout: float = Query(120.0, description="请求超时时间(秒)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重置LLM速度限制器实例（使用新配置）"""
    try:
        # 重置全局实例
        reset_llm_rate_limiter()
        
        # 创建新实例
        rate_limiter = get_llm_rate_limiter(
            max_concurrent_requests=max_concurrent,
            min_interval_seconds=min_interval,
            request_timeout_seconds=timeout
        )
        
        logger.info(
            f"用户 {current_user.username} 重置了LLM速度限制器: "
            f"max_concurrent={max_concurrent}, min_interval={min_interval}s, timeout={timeout}s"
        )
        
        return ApiResponse(
            success=True,
            data={
                "new_config": {
                    "max_concurrent_requests": max_concurrent,
                    "min_interval_seconds": min_interval,
                    "request_timeout_seconds": timeout
                }
            },
            message="LLM速度限制器重置成功"
        )
    except Exception as e:
        logger.error(f"重置LLM速度限制器失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.get("/health", response_model=ApiResponse)
async def llm_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """LLM服务健康检查"""
    try:
        # 检查速度限制器
        rate_limiter = get_llm_rate_limiter()
        limiter_health = await rate_limiter.health_check()
        
        # 检查AI服务连接池
        pool = get_ai_service_pool()
        pool_stats = pool.get_pool_stats()
        
        # 综合健康状态
        overall_status = "healthy"
        issues = []
        
        if limiter_health['status'] in ['warning', 'busy']:
            overall_status = limiter_health['status']
            issues.extend(limiter_health.get('issues', []))
        
        if pool_stats['total_instances'] == 0:
            issues.append("AI服务连接池无活跃实例")
            overall_status = "warning"
        
        health_data = {
            "overall_status": overall_status,
            "rate_limiter": limiter_health,
            "ai_service_pool": {
                "total_instances": pool_stats['total_instances'],
                "max_instances": pool_stats['max_instances'],
                "active_references": pool_stats['active_references']
            },
            "issues": issues
        }
        
        return ApiResponse(
            success=True,
            data=health_data,
            message="健康检查完成"
        )
    except Exception as e:
        logger.error(f"LLM健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/config", response_model=ApiResponse)
async def get_llm_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前LLM配置"""
    try:
        rate_limiter = get_llm_rate_limiter()
        stats = rate_limiter.get_statistics()
        
        config_data = {
            "rate_limiter_config": stats['rate_limiter_config'],
            "creation_time": getattr(rate_limiter, '_start_time', None),
            "current_status": stats['current_status']
        }
        
        return ApiResponse(
            success=True,
            data=config_data,
            message="LLM配置获取成功"
        )
    except Exception as e:
        logger.error(f"获取LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")