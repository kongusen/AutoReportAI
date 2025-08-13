"""
Task调度管理API端点
提供Task调度的创建、更新、删除和状态查询功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app import crud
from app.schemas.task import TaskCreate, TaskUpdate

router = APIRouter()


@router.post("/schedule", response_model=ApiResponse)
async def create_task_schedule(
    task_id: int,
    cron_expression: str = Query(..., description="Cron表达式，如: 0 9 * * 1-5"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为Task创建调度"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证Task存在且用户有权限
    task = crud.task.get(db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限操作此任务"
        )
    
    try:
        # 更新Task的调度字段
        task_update = TaskUpdate(schedule=cron_expression)
        updated_task = crud.task.update(db, db_obj=task, obj_in=task_update)
        
        # 在统一调度器中注册
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            await scheduler.add_or_update_task(task_id, cron_expression)
            
            next_run_info = await scheduler.get_task_status(task_id)
        except Exception as scheduler_error:
            # 如果调度器有问题，至少数据库更新成功了
            next_run_info = {"message": f"数据库更新成功，但调度器注册失败: {scheduler_error}"}
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "task_name": updated_task.name,
                "schedule": cron_expression,
                "status": "scheduled",
                "next_run_info": next_run_info
            },
            message=f"任务 '{updated_task.name}' 调度创建成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建调度失败: {str(e)}"
        )


@router.put("/schedule/{task_id}", response_model=ApiResponse)
async def update_task_schedule(
    task_id: int,
    cron_expression: str = Query(..., description="新的Cron表达式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新Task调度"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证权限
    task = crud.task.get(db, id=task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限"
        )
    
    try:
        # 更新数据库
        task_update = TaskUpdate(schedule=cron_expression)
        updated_task = crud.task.update(db, db_obj=task, obj_in=task_update)
        
        # 更新统一调度器
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            await scheduler.add_or_update_task(task_id, cron_expression)
            
            next_run_info = await scheduler.get_task_status(task_id)
        except Exception as scheduler_error:
            next_run_info = {"message": f"数据库更新成功，但调度器更新失败: {scheduler_error}"}
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "task_name": updated_task.name,
                "schedule": cron_expression,
                "status": "rescheduled",
                "next_run_info": next_run_info
            },
            message="任务调度更新成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新调度失败: {str(e)}"
        )


@router.delete("/schedule/{task_id}", response_model=ApiResponse)
async def remove_task_schedule(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """移除Task调度"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证权限
    task = crud.task.get(db, id=task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限"
        )
    
    try:
        # 从统一调度器中移除
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            await scheduler.remove_task(task_id)
        except Exception as scheduler_error:
            # 即使调度器移除失败，仍然更新数据库
            pass
        
        # 更新数据库（清除schedule字段）
        task_update = TaskUpdate(schedule=None)
        updated_task = crud.task.update(db, db_obj=task, obj_in=task_update)
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "task_name": updated_task.name,
                "status": "unscheduled"
            },
            message="任务调度已移除"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除调度失败: {str(e)}"
        )


@router.post("/execute/{task_id}", response_model=ApiResponse)
async def execute_task_immediately(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """立即执行Task（智能占位符分析）"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证权限
    task = crud.task.get(db, id=task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限"
        )
    
    if not task.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务已禁用"
        )
    
    try:
        # 执行任务 - 使用统一调度器
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            result = await scheduler.execute_task_immediately(task_id, str(user_id))
        except Exception as scheduler_error:
            result = {"status": "error", "message": f"统一调度器不可用: {scheduler_error}"}
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return ApiResponse(
            success=True,
            data=result,
            message="任务执行已启动"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行任务失败: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=ApiResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取Task执行状态"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证权限
    task = crud.task.get(db, id=task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限"
        )
    
    try:
        # 获取任务状态 - 使用统一调度器
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            status_info = await scheduler.get_task_status(task_id)
        except Exception as scheduler_error:
            status_info = {
                "task_id": task_id,
                "status": "unknown",
                "message": f"统一调度器不可用: {scheduler_error}"
            }
        
        return ApiResponse(
            success=True,
            data=status_info,
            message="获取任务状态成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.get("/scheduled", response_model=ApiResponse)
async def get_scheduled_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有已调度任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    try:
        # 从数据库获取用户的已调度任务
        tasks = db.query(Task).filter(
            Task.owner_id == user_id,
            Task.schedule.isnot(None),
            Task.is_active == True
        ).all()
        
        # 获取统一调度器信息
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            scheduler_info = await scheduler.get_scheduler_info()
        except Exception as scheduler_error:
            scheduler_info = {}
        
        # 结合数据库和调度器信息
        scheduled_info = {
            "total_scheduled": len(tasks),
            "database_tasks": [
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "schedule": task.schedule,
                    "status": "scheduled"
                }
                for task in tasks
            ],
            "scheduler_tasks": scheduler_info
        }
        
        return ApiResponse(
            success=True,
            data=scheduled_info,
            message="获取已调度任务列表成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取已调度任务失败: {str(e)}"
        )


@router.get("/active", response_model=ApiResponse)
async def get_active_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有活跃任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    try:
        # 从数据库获取用户的活跃任务
        tasks = db.query(Task).filter(
            Task.owner_id == user_id,
            Task.is_active == True
        ).all()
        
        # 获取统一调度器的活跃任务信息
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()
            scheduler_info = await scheduler.get_scheduler_info()
            active_tasks_from_scheduler = scheduler.active_tasks
        except Exception as scheduler_error:
            active_tasks_from_scheduler = {}

        return ApiResponse(
            success=True,
            data={
                "database_active_count": len(tasks),
                "scheduler_active_count": len(active_tasks_from_scheduler),
                "active_tasks": active_tasks_from_scheduler
            },
            message="获取活跃任务列表成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取活跃任务失败: {str(e)}"
        )


@router.post("/reload", response_model=ApiResponse)
async def reload_task_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新加载所有任务调度（管理员功能）"""
    # 检查用户权限（这里可以添加管理员权限检查）
    
    try:
        # 重新加载调度 - 使用统一调度器
        from app.core.unified_scheduler import get_scheduler
        scheduler = await get_scheduler()
        await scheduler.reload_all_tasks()
        
        # 获取重新加载后的状态
        scheduled_tasks_info = await scheduler.get_scheduler_info()
        
        return ApiResponse(
            success=True,
            data={
                "message": "任务调度重新加载成功",
                "scheduled_tasks": scheduled_tasks_info
            },
            message="任务调度重新加载成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载任务调度失败: {str(e)}"
        )