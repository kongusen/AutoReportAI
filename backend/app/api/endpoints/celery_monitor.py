"""
Celery 监控和管理 API 端点
提供任务调度的监控、管理功能
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.core.celery_scheduler import get_scheduler_manager
from app.services.application.task_management.core.worker import celery_app
from app.models.user import User
from app.schemas.base import APIResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/workers/status", response_model=APIResponse)
def get_workers_status(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取 Celery Workers 状态"""
    try:
        manager = get_scheduler_manager(celery_app)
        stats = manager.get_worker_stats()
        
        return APIResponse(
            success=True,
            data=stats,
            message="Workers 状态获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取 Workers 状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取 Workers 状态失败: {str(e)}")


@router.get("/tasks/scheduled", response_model=APIResponse)
def get_scheduled_tasks(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取所有调度任务信息"""
    try:
        manager = get_scheduler_manager(celery_app)
        tasks = manager.get_all_scheduled_tasks()
        
        return APIResponse(
            success=True,
            data=tasks,
            message=f"获取了 {len(tasks)} 个调度任务信息"
        )
        
    except Exception as e:
        logger.error(f"获取调度任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度任务失败: {str(e)}")


@router.get("/tasks/{task_id}/status", response_model=APIResponse)
def get_task_status(
    task_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取指定任务的状态"""
    try:
        manager = get_scheduler_manager(celery_app)
        status = manager.get_task_status(task_id)
        
        return APIResponse(
            success=True,
            data=status,
            message=f"任务 {task_id} 状态获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取任务 {task_id} 状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.post("/tasks/{task_id}/execute", response_model=APIResponse)
def execute_task_immediately(
    task_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """立即执行指定任务"""
    try:
        manager = get_scheduler_manager(celery_app)
        result = manager.execute_task_immediately(task_id, str(current_user.id))
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return APIResponse(
            success=True,
            data=result,
            message=f"任务 {task_id} 已提交执行"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行任务失败: {str(e)}")


@router.post("/tasks/{task_id}/schedule", response_model=APIResponse)
def update_task_schedule(
    task_id: int,
    cron_expression: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新任务调度"""
    try:
        # 验证任务存在和权限
        task = crud.task.get(db, id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        # 更新调度
        manager = get_scheduler_manager(celery_app)
        success = manager.add_or_update_task(task_id, cron_expression)
        
        if not success:
            raise HTTPException(status_code=400, detail="更新任务调度失败")
            
        return APIResponse(
            success=True,
            data={"task_id": task_id, "schedule": cron_expression},
            message=f"任务 {task_id} 调度已更新"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务 {task_id} 调度失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新任务调度失败: {str(e)}")


@router.delete("/tasks/{task_id}/schedule", response_model=APIResponse)
def remove_task_schedule(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """移除任务调度"""
    try:
        # 验证任务存在和权限
        task = crud.task.get(db, id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        # 移除调度
        manager = get_scheduler_manager(celery_app)
        success = manager.remove_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="移除任务调度失败")
            
        return APIResponse(
            success=True,
            data={"task_id": task_id},
            message=f"任务 {task_id} 调度已移除"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除任务 {task_id} 调度失败: {e}")
        raise HTTPException(status_code=500, detail=f"移除任务调度失败: {str(e)}")


@router.post("/scheduler/reload", response_model=APIResponse)
def reload_scheduler(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """重新加载调度器"""
    try:
        manager = get_scheduler_manager(celery_app)
        loaded_count = manager.load_scheduled_tasks_from_database()
        
        return APIResponse(
            success=True,
            data={"loaded_tasks": loaded_count},
            message=f"调度器已重新加载，加载了 {loaded_count} 个任务"
        )
        
    except Exception as e:
        logger.error(f"重新加载调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载调度器失败: {str(e)}")


@router.get("/inspect/active", response_model=APIResponse)
def inspect_active_tasks(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """查看活跃的任务"""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        return APIResponse(
            success=True,
            data=active_tasks or {},
            message="活跃任务查询成功"
        )
        
    except Exception as e:
        logger.error(f"查看活跃任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"查看活跃任务失败: {str(e)}")


@router.get("/inspect/stats", response_model=APIResponse)
def inspect_worker_stats(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """查看 Worker 统计信息"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        return APIResponse(
            success=True,
            data=stats or {},
            message="Worker 统计信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"查看 Worker 统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"查看 Worker 统计信息失败: {str(e)}")


@router.get("/inspect/registered", response_model=APIResponse)
def inspect_registered_tasks(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """查看已注册的任务"""
    try:
        inspect = celery_app.control.inspect()
        registered = inspect.registered()
        
        return APIResponse(
            success=True,
            data=registered or {},
            message="已注册任务查询成功"
        )
        
    except Exception as e:
        logger.error(f"查看已注册任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"查看已注册任务失败: {str(e)}")


@router.get("/beat/schedule", response_model=APIResponse)
def get_beat_schedule(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """查看 Celery Beat 调度信息"""
    try:
        beat_schedule = {}
        
        for task_name, config in celery_app.conf.beat_schedule.items():
            beat_schedule[task_name] = {
                "task": config["task"],
                "schedule": str(config["schedule"]),
                "args": config.get("args", []),
                "kwargs": config.get("kwargs", {}),
                "options": config.get("options", {})
            }
        
        return APIResponse(
            success=True,
            data=beat_schedule,
            message=f"Beat 调度信息查询成功，共 {len(beat_schedule)} 个任务"
        )
        
    except Exception as e:
        logger.error(f"查看 Beat 调度信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"查看 Beat 调度信息失败: {str(e)}")