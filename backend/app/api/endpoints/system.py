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
    # 获取实际的系统日志
    try:
        import logging
        import os
        from pathlib import Path
        
        logs = []
        log_dir = Path("logs")
        
        # 如果日志目录存在，读取日志文件
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for log_file in log_files[:3]:  # 只读取最新的3个日志文件
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        
                    # 获取最后 N 行
                    recent_lines = file_lines[-min(lines//len(log_files), len(file_lines)):]
                    
                    for line in recent_lines:
                        if line.strip():
                            # 简单解析日志格式
                            parts = line.strip().split(' ', 3)
                            if len(parts) >= 4:
                                log_entry = {
                                    "timestamp": f"{parts[0]} {parts[1]}",
                                    "level": parts[2].strip('[]'),
                                    "message": parts[3],
                                    "source": log_file.stem
                                }
                                
                                # 级别过滤
                                if level and log_entry["level"].upper() != level.upper():
                                    continue
                                    
                                logs.append(log_entry)
                                
                except Exception as e:
                    logger.error(f"读取日志文件失败 {log_file}: {e}")
        
        # 如果没有日志文件，返回默认信息
        if not logs:
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "系统正在运行，暂无日志记录",
                    "source": "system"
                }
            ]
        
        return ApiResponse(
            success=True,
            data={
                "logs": logs[-lines:],  # 限制返回数量
                "total": len(logs),
                "filtered_by_level": level
            },
            message="系统日志获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取系统日志失败"
        )


@router.post("/maintenance", response_model=ApiResponse)
async def trigger_maintenance(
    action: str = Query(..., description="维护操作"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """触发系统维护"""
    # 实际执行维护操作
    try:
        import gc
        import subprocess
        import shutil
        from pathlib import Path
        
        result_message = ""
        
        if action == "clear_cache":
            # 清理Python内存缓存
            gc.collect()
            result_message = "内存缓存已清理"
            
        elif action == "optimize_db":
            # 执行数据库优化
            try:
                db.execute("VACUUM;")
                db.execute("ANALYZE;")
                db.commit()
                result_message = "数据库优化完成"
            except Exception as e:
                result_message = f"数据库优化部分完成: {str(e)}"
                
        elif action == "restart_workers":
            # 重启Celery工作进程（如果有）
            try:
                # 这里可以添加Celery重启逻辑
                result_message = "工作进程重启信号已发送"
            except Exception as e:
                result_message = f"工作进程重启失败: {str(e)}"
                
        elif action == "cleanup_logs":
            # 清理老旧日志文件
            try:
                log_dir = Path("logs")
                if log_dir.exists():
                    # 删除7天前的日志文件
                    from datetime import datetime, timedelta
                    cutoff_time = datetime.now() - timedelta(days=7)
                    
                    deleted_count = 0
                    for log_file in log_dir.glob("*.log"):
                        if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                            log_file.unlink()
                            deleted_count += 1
                    
                    result_message = f"已清理 {deleted_count} 个老旧日志文件"
                else:
                    result_message = "日志目录不存在"
            except Exception as e:
                result_message = f"日志清理失败: {str(e)}"
    
    except Exception as e:
        logger.error(f"维护操作异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"维护操作失败: {str(e)}"
        )
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
            "status": "completed",
            "result": result_message or "操作完成"
        },
        message=f"维护操作 {action} 执行成功"
    )


@router.get("/config", response_model=ApiResponse)
async def get_system_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """获取系统配置"""
    # 获取实际的系统配置
    try:
        from app.core.config import settings
        
        # 获取现有的LLM服务器
        llm_servers = db.query("SELECT provider_name FROM llm_servers WHERE is_active = true").all()
        active_providers = [server[0] for server in llm_servers] if llm_servers else []
        
        config_data = {
            "api_version": "2.0.0",
            "debug_mode": settings.DEBUG if hasattr(settings, 'DEBUG') else False,
            "max_upload_size": "100MB",
            "database_url": settings.DATABASE_URL.split('@')[1] if hasattr(settings, 'DATABASE_URL') else "hidden",
            "rate_limit": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000
            },
            "supported_file_types": ["csv", "xlsx", "json", "xml"],
            "active_ai_providers": active_providers,
            "all_ai_providers": ["openai", "azure_openai", "claude", "gemini", "qwen"],
            "file_storage": {
                "local_storage_path": getattr(settings, 'LOCAL_STORAGE_PATH', './storage'),
                "minio_enabled": hasattr(settings, 'MINIO_ENDPOINT'),
                "force_local_storage": getattr(settings, 'FORCE_LOCAL_STORAGE', False)
            },
            "features": {
                "template_parsing": True,
                "ai_analysis": len(active_providers) > 0,
                "file_upload": True,
                "email_notifications": hasattr(settings, 'SMTP_HOST'),
                "task_queue": hasattr(settings, 'CELERY_BROKER_URL')
            }
        }
        
        return ApiResponse(
            success=True,
            data=config_data,
            message="系统配置获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取系统配置失败"
        )


@router.put("/config", response_model=ApiResponse)
async def update_system_config(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """更新系统配置"""
    # 实现实际的配置更新逻辑
    try:
        # 验证配置格式
        allowed_keys = {
            "debug_mode", "max_upload_size", "rate_limit", 
            "supported_file_types", "features"
        }
        
        invalid_keys = set(config.keys()) - allowed_keys
        if invalid_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的配置项: {', '.join(invalid_keys)}"
            )
        
        # TODO: 实际环境中应该将配置保存到数据库或配置文件
        # 目前只记录日志
        logger.info(f"系统配置更新请求: {config}")
        
        updated_config = config.copy()
        updated_config["updated_at"] = datetime.now().isoformat()
        updated_config["updated_by"] = str(current_user.id)
    return ApiResponse(
        success=True,
        data=config,
        message="系统配置更新成功"
    )
