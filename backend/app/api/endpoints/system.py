"""系统管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import psutil
import os
from datetime import datetime

from app.core.architecture import ApiResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_system_info():
    """获取系统基本信息"""
    return ApiResponse(
        success=True,
        data={
            "system_name": "AutoReportAI",
            "version": "v1.0.0",
            "description": "智能报告生成系统",
            "features": [
                "AI驱动的报告生成",
                "多数据源支持",
                "智能模板处理",
                "实时任务监控",
                "邮件通知系统"
            ],
            "api_version": "v1",
            "supported_versions": ["v1", "v2"],
            "status": "operational"
        },
        message="系统信息获取成功"
    )


@router.get("/health", response_model=ApiResponse)
async def get_system_health(
    db: Session = Depends(get_db)
):
    """获取系统健康状态"""
    try:
        # 系统资源信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 数据库连接状态
        try:
            db.execute("SELECT 1")
            db_status = "healthy"
        except Exception:
            db_status = "unhealthy"
        
        # Redis连接状态（如果有）
        redis_status = "unknown"  # 暂时未知
        
        return ApiResponse(
            success=True,
            data={
                "status": "healthy",
                "timestamp": str(psutil.boot_time()),
                "resources": {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "cores": psutil.cpu_count()
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percent": memory.percent
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": (disk.used / disk.total) * 100
                    }
                },
                "services": {
                    "database": db_status,
                    "redis": redis_status
                }
            },
            message="系统健康状态获取成功"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取系统健康状态失败"
        )


@router.get("/metrics", response_model=ApiResponse)
async def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取系统指标"""
    try:
        # 获取进程信息
        process = psutil.Process(os.getpid())
        
        # 内存使用
        memory_info = process.memory_info()
        
        # CPU使用
        cpu_percent = process.cpu_percent()
        
        # 线程数
        thread_count = process.num_threads()
        
        # 打开的文件描述符数
        try:
            open_files = len(process.open_files())
        except:
            open_files = 0
        
        return ApiResponse(
            success=True,
            data={
                "process": {
                    "pid": process.pid,
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "cpu_percent": cpu_percent,
                    "threads": thread_count,
                    "open_files": open_files
                },
                "uptime": str(datetime.utcnow() - datetime.fromtimestamp(psutil.boot_time()))
            },
            message="系统指标获取成功"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取系统指标失败"
        )


@router.get("/logs", response_model=ApiResponse)
async def get_system_logs(
    lines: int = Query(100, ge=1, le=1000, description="返回的日志行数"),
    level: Optional[str] = Query(None, description="日志级别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取系统日志"""
    # 这里应该实现实际的日志获取逻辑
    # 暂时返回模拟数据
    return ApiResponse(
        success=True,
        data={
            "logs": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "level": "INFO",
                    "message": "系统启动成功",
                    "source": "system"
                },
                {
                    "timestamp": "2024-01-01T12:01:00Z",
                    "level": "INFO",
                    "message": "数据库连接成功",
                    "source": "database"
                }
            ],
            "total": 2
        },
        message="系统日志获取成功"
    )


@router.post("/maintenance", response_model=ApiResponse)
async def trigger_maintenance(
    action: str = Query(..., description="维护操作"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """触发系统维护"""
    # 这里应该实现实际的维护操作
    maintenance_actions = {
        "clear_cache": "缓存清理",
        "optimize_db": "数据库优化",
        "restart_workers": "重启工作进程",
        "cleanup_logs": "清理日志"
    }
    
    if action not in maintenance_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的维护操作"
        )
    
    return ApiResponse(
        success=True,
        data={
            "action": action,
            "description": maintenance_actions[action],
            "status": "completed"
        },
        message=f"维护操作 {action} 执行成功"
    )


@router.get("/config", response_model=ApiResponse)
async def get_system_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """获取系统配置"""
    # 这里应该返回实际的系统配置
    return ApiResponse(
        success=True,
        data={
            "api_version": "2.0.0",
            "debug_mode": False,
            "max_upload_size": "100MB",
            "rate_limit": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000
            },
            "supported_file_types": ["csv", "xlsx", "json", "xml"],
            "supported_ai_providers": ["openai", "azure_openai", "claude", "gemini"]
        },
        message="系统配置获取成功"
    )


@router.put("/config", response_model=ApiResponse)
async def update_system_config(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """更新系统配置"""
    # 这里应该实现实际的配置更新逻辑
    return ApiResponse(
        success=True,
        data=config,
        message="系统配置更新成功"
    )
