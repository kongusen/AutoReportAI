from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.base_api_controller import CRUDAPIController, APIResponse, PaginatedAPIResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.application.tasks.task_application_service import TaskApplicationService
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.application.factories import create_placeholder_validation_service
from app.services.data.query.query_executor_service import query_executor_service
from app.services.infrastructure.document.word_export_service import create_word_export_service
from app.services.data.persistence.etl_persistence_service import ETLPersistenceService
from app.schemas.placeholder_value import PlaceholderValueCreate
from app.utils.time_context import TimeContextManager
from app import crud
import time as _time
import os as _os
from decimal import Decimal

logger = logging.getLogger(__name__)
router = APIRouter()

# 创建任务控制器实例
task_controller = CRUDAPIController("任务", "TaskController")


@router.get("/", response_model=PaginatedAPIResponse)
async def get_tasks(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 构建查询
    query = db.query(Task).filter(Task.owner_id == user_id)

    
    # 应用过滤器
    if is_active is not None:
        query = query.filter(Task.is_active == is_active)
    
    if search:
        query = query.filter(
            Task.name.contains(search) |
            Task.description.contains(search)
        )
    
    # 获取总数
    total = query.count()
    
    # 应用分页并获取结果
    tasks = query.offset(skip).limit(limit).all()
    
    # 转换为TaskResponse格式，保持向后兼容，并包含执行状态
    task_dicts = []
    for task in tasks:
        # 获取最新的执行记录
        from app.models.task import TaskExecution
        latest_execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task.id
        ).order_by(TaskExecution.created_at.desc()).first()

        # 确定当前执行状态
        current_execution_status = None
        current_progress = 0
        current_step = None
        execution_id = None
        celery_task_id = None

        if latest_execution:
            current_execution_status = latest_execution.execution_status.value
            current_progress = latest_execution.progress_percentage or 0
            current_step = latest_execution.current_step
            execution_id = str(latest_execution.execution_id)
            celery_task_id = latest_execution.celery_task_id

        # 构建兼容的任务数据，包含新字段但有默认值
        task_dict = {
            # 原有字段
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "template_id": str(task.template_id) if task.template_id else None,
            "data_source_id": str(task.data_source_id) if task.data_source_id else None,
            "schedule": task.schedule,
            "report_period": task.report_period.value if task.report_period else "monthly",
            "recipients": task.recipients or [],
            "owner_id": str(task.owner_id) if task.owner_id else None,
            "is_active": task.is_active,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "unique_id": str(task.id),

            # 任务状态字段
            "status": task.status.value if hasattr(task, 'status') and task.status else "pending",

            # 当前执行状态（重要：前端需要这些信息来判断任务是否在执行）
            "current_execution_status": current_execution_status,
            "current_execution_progress": current_progress,
            "current_execution_step": current_step,
            "current_execution_id": execution_id,
            "current_celery_task_id": celery_task_id,
            "is_executing": current_execution_status in ["processing", "pending"] if current_execution_status else False,

            # 其他新增字段
            "processing_mode": task.processing_mode.value if hasattr(task, 'processing_mode') and task.processing_mode else "intelligent",
            "workflow_type": task.workflow_type.value if hasattr(task, 'workflow_type') and task.workflow_type else "simple_report",
            "execution_count": getattr(task, 'execution_count', 0),
            "success_count": getattr(task, 'success_count', 0),
            "failure_count": getattr(task, 'failure_count', 0),
            "success_rate": task.success_rate if hasattr(task, 'success_rate') else 0.0,
            "last_execution_at": task.last_execution_at.isoformat() if hasattr(task, 'last_execution_at') and task.last_execution_at else None,
            "average_execution_time": getattr(task, 'average_execution_time', 0.0),
            "max_context_tokens": getattr(task, 'max_context_tokens', 32000),
            "enable_compression": getattr(task, 'enable_compression', True)
        }
        task_dicts.append(task_dict)
    
    # 直接返回分页响应，避免双重包装
    return PaginatedAPIResponse.create(
        items=task_dicts,
        total=total,
        page=skip // limit + 1,
        size=limit,
        message="获取任务列表成功"
    )


@router.post("/", response_model=APIResponse[TaskResponse])
async def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建任务"""
    task_controller.log_api_request("create_task", user_id=str(current_user.id))
    
    task_service = TaskApplicationService()

    # 调用应用服务
    app_result = task_service.create_task(
        db=db,
        user_id=str(current_user.id),
        name=task_in.name,
        template_id=str(task_in.template_id),
        data_source_id=str(task_in.data_source_id),
        description=task_in.description,
        schedule=task_in.schedule,
        recipients=task_in.recipients,
        is_active=task_in.is_active,
        processing_mode=task_in.processing_mode,
        workflow_type=task_in.workflow_type,
        max_context_tokens=task_in.max_context_tokens,
        enable_compression=task_in.enable_compression
    )
    
    # 使用控制器处理结果
    return task_controller.handle_application_result(app_result)


@router.put("/{task_id}", response_model=APIResponse[TaskResponse])
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        # 获取更新数据
        update_data = task_in.model_dump(exclude_unset=True)
        
        task = task_service.update_task(
            db=db,
            task_id=task_id,
            user_id=user_id,
            **update_data
        )
        
        task_schema = TaskResponse.model_validate(task)
        task_dict = task_schema.model_dump()
        return APIResponse(
            success=True,
            data=task_dict,
            message="任务更新成功"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="任务更新失败"
        )


@router.get("/{task_id}", response_model=APIResponse[TaskResponse])
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_schema = TaskResponse.model_validate(task)
    task_dict = task_schema.model_dump()
    return APIResponse(
        success=True,
        data=task_dict,
        message="获取任务成功"
    )


@router.delete("/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)

        success = task_service.delete_task(
            db=db,
            task_id=task_id,
            user_id=user_id
        )

        return APIResponse(
            success=True,
            data={"task_id": task_id, "deleted": success},
            message="任务删除成功"
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message="任务删除失败"
        )


@router.post("/{task_id}/execute", response_model=APIResponse[Dict[str, Any]])
async def execute_task(
    task_id: int,
    execution_time: Optional[str] = Query(None, description="任务执行时间 (YYYY-MM-DD HH:MM:SS，默认为当前时间)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行任务 - 使用新的TaskApplicationService"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        # 构建执行上下文
        execution_context = {}
        if execution_time:
            try:
                parsed_execution_time = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
                execution_context["execution_time"] = parsed_execution_time.isoformat()
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"无效的时间格式: {str(e)}")
        
        # 执行任务
        result = task_service.execute_task_immediately(
            db=db,
            task_id=task_id,
            user_id=user_id,
            execution_context=execution_context
        )
        
        return APIResponse(
            success=True,
            data=result,
            message="任务执行请求已提交"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="任务执行失败"
        )


@router.post("/{task_id}/pause", response_model=APIResponse[Dict[str, Any]])
async def pause_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """暂停任务（将 is_active 置为 False 并从调度器移除）"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或无权限")

        if task.is_active is False:
            return APIResponse(success=True, data={"task_id": task_id, "is_active": task.is_active}, message="任务已处于暂停状态")

        # 1. 更新数据库状态
        task.is_active = False
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

        # 2. 从调度器移除（如果有调度）
        scheduler_result = {"scheduler_removed": False, "message": ""}
        if task.schedule:
            try:
                from app.core.unified_scheduler import get_scheduler
                scheduler = await get_scheduler()
                await scheduler.remove_task(task_id)
                scheduler_result = {
                    "scheduler_removed": True,
                    "message": f"已从调度器移除任务 {task_id}"
                }
                logger.info(f"✅ 任务 {task_id} 已从调度器移除")
            except Exception as scheduler_error:
                logger.warning(f"⚠️ 从调度器移除任务 {task_id} 失败: {scheduler_error}")
                scheduler_result = {
                    "scheduler_removed": False,
                    "message": f"调度器操作失败: {str(scheduler_error)}"
                }

        # 3. 可选：取消正在执行的任务
        cancelled_execution = None
        try:
            from app.models.task import TaskExecution, TaskStatus
            ongoing_execution = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
            ).first()

            if ongoing_execution and ongoing_execution.celery_task_id:
                from app.services.infrastructure.task_queue.celery_config import celery_app
                celery_app.control.revoke(ongoing_execution.celery_task_id, terminate=True)
                ongoing_execution.execution_status = TaskStatus.CANCELLED
                ongoing_execution.current_step = "任务已被暂停操作取消"
                ongoing_execution.completed_at = datetime.utcnow()
                db.commit()
                cancelled_execution = str(ongoing_execution.execution_id)
                logger.info(f"✅ 取消了正在执行的任务: {ongoing_execution.celery_task_id}")
        except Exception as cancel_error:
            logger.warning(f"⚠️ 取消执行任务失败: {cancel_error}")

        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "is_active": task.is_active,
                "scheduler_status": scheduler_result,
                "cancelled_execution_id": cancelled_execution
            },
            message="任务已暂停"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 暂停任务失败: {e}")
        db.rollback()
        return APIResponse(success=False, data=None, errors=[str(e)], message="暂停任务失败")


@router.post("/{task_id}/resume", response_model=APIResponse[Dict[str, Any]])
async def resume_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """恢复任务（将 is_active 置为 True 并重新添加到调度器）"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或无权限")

        if task.is_active is True:
            return APIResponse(success=True, data={"task_id": task_id, "is_active": task.is_active}, message="任务已处于启用状态")

        # 1. 更新数据库状态
        task.is_active = True
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

        # 2. 添加到调度器（如果有调度）
        scheduler_result = {"scheduler_added": False, "message": ""}
        if task.schedule:
            try:
                from app.core.unified_scheduler import get_scheduler
                scheduler = await get_scheduler()
                await scheduler.add_or_update_task(task_id, task.schedule)

                # 获取下次执行时间
                task_status = await scheduler.get_task_status(task_id)
                next_run_time = task_status.get("next_run_time")

                scheduler_result = {
                    "scheduler_added": True,
                    "message": f"已添加到调度器",
                    "next_run_time": next_run_time
                }
                logger.info(f"✅ 任务 {task_id} 已添加到调度器，下次执行: {next_run_time}")
            except Exception as scheduler_error:
                logger.warning(f"⚠️ 添加任务 {task_id} 到调度器失败: {scheduler_error}")
                scheduler_result = {
                    "scheduler_added": False,
                    "message": f"调度器操作失败: {str(scheduler_error)}"
                }
        else:
            scheduler_result = {
                "scheduler_added": False,
                "message": "任务未设置调度表达式，无需添加到调度器"
            }

        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "is_active": task.is_active,
                "scheduler_status": scheduler_result
            },
            message="任务已恢复"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 恢复任务失败: {e}")
        db.rollback()
        return APIResponse(success=False, data=None, errors=[str(e)], message="恢复任务失败")


@router.post("/{task_id}/run", response_model=APIResponse[Dict[str, Any]])
async def run_task(
    task_id: int,
    execution_time: Optional[str] = Query(None, description="任务执行时间 (YYYY-MM-DD HH:MM:SS，默认为当前时间)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行任务 - /execute 接口的别名，提供更直观的接口"""
    # 直接调用 execute_task 函数，复用相同的逻辑
    return await execute_task(task_id, execution_time, db, current_user)


@router.get("/{task_id}/executions", response_model=APIResponse)
async def get_task_executions(
    task_id: int,
    limit: int = Query(50, ge=1, le=100, description="返回记录数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务执行历史"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        executions = task_service.get_task_executions(
            db=db,
            task_id=task_id,
            user_id=user_id,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "executions": executions
            },
            message="获取执行历史成功"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="获取执行历史失败"
        )


@router.post("/{task_id}/validate", response_model=APIResponse)
async def validate_task_configuration(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """验证任务配置（包括占位符验证）"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        validation_result = task_service.validate_task_configuration(
            db=db,
            task_id=task_id,
            user_id=user_id
        )
        
        return APIResponse(
            success=True,
            data=validation_result,
            message="任务配置验证已启动"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="任务配置验证失败"
        )


@router.post("/{task_id}/schedule", response_model=APIResponse)
async def schedule_task(
    task_id: int,
    schedule: str = Query(..., description="Cron表达式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置任务调度"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        result = task_service.schedule_task(
            db=db,
            task_id=task_id,
            schedule=schedule,
            user_id=user_id
        )
        
        return APIResponse(
            success=True,
            data=result,
            message="任务调度设置成功"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="任务调度设置失败"
        )


@router.get("/{task_id}/status", response_model=APIResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务执行状态"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)

        status_data = task_service.get_task_status(
            db=db,
            task_id=task_id,
            user_id=user_id
        )

        return APIResponse(
            success=True,
            data=status_data,
            message="获取任务状态成功"
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="获取任务状态失败"
        )


@router.get("/{task_id}/progress", response_model=APIResponse)
async def get_task_progress(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务执行进度"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        # 获取任务权限验证
        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或无权限")

        # 获取最新的执行记录
        from app.models.task import TaskExecution
        latest_execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id
        ).order_by(TaskExecution.created_at.desc()).first()

        if not latest_execution:
            return APIResponse(
                success=True,
                data={
                    "task_id": task_id,
                    "progress_percentage": 0,
                    "current_step": "未开始执行",
                    "execution_status": "pending",
                    "started_at": None,
                    "estimated_completion": None
                },
                message="获取任务进度成功"
            )

        # 估算完成时间
        estimated_completion = None
        if latest_execution.started_at and latest_execution.progress_percentage > 0:
            elapsed_seconds = (datetime.utcnow() - latest_execution.started_at).total_seconds()
            if latest_execution.progress_percentage > 0:
                estimated_total_seconds = (elapsed_seconds / latest_execution.progress_percentage) * 100
                estimated_remaining_seconds = estimated_total_seconds - elapsed_seconds
                if estimated_remaining_seconds > 0:
                    estimated_completion = (datetime.utcnow() + timedelta(seconds=estimated_remaining_seconds)).isoformat()

        progress_data = {
            "task_id": task_id,
            "execution_id": str(latest_execution.execution_id),
            "progress_percentage": latest_execution.progress_percentage,
            "current_step": latest_execution.current_step or "执行中...",
            "execution_status": latest_execution.execution_status.value,
            "started_at": latest_execution.started_at.isoformat() if latest_execution.started_at else None,
            "completed_at": latest_execution.completed_at.isoformat() if latest_execution.completed_at else None,
            "estimated_completion": estimated_completion,
            "celery_task_id": latest_execution.celery_task_id,
            "error_details": latest_execution.error_details
        }

        return APIResponse(
            success=True,
            data=progress_data,
            message="获取任务进度成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="获取任务进度失败"
        )


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_task_execution(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消/暂停任务执行"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        # 获取任务权限验证
        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或无权限")

        # 获取最新的执行记录
        from app.models.task import TaskExecution
        latest_execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id,
            TaskExecution.execution_status.in_(['processing', 'pending'])
        ).order_by(TaskExecution.created_at.desc()).first()

        if not latest_execution:
            return APIResponse(
                success=False,
                data=None,
                message="没有正在执行的任务可以取消"
            )

        # 尝试取消Celery任务
        if latest_execution.celery_task_id:
            try:
                from app.services.infrastructure.task_queue.celery_config import celery_app
                celery_app.control.revoke(latest_execution.celery_task_id, terminate=True)
                logger.info(f"Cancelled Celery task {latest_execution.celery_task_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel Celery task: {e}")

        # 更新执行状态
        from app.models.task import TaskStatus
        latest_execution.execution_status = TaskStatus.CANCELLED
        latest_execution.current_step = "任务已被用户取消"
        latest_execution.completed_at = datetime.utcnow()
        latest_execution.total_duration = int(
            (latest_execution.completed_at - latest_execution.started_at).total_seconds()
        ) if latest_execution.started_at else 0

        # 更新任务状态
        task.status = TaskStatus.CANCELLED

        db.commit()

        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "execution_id": str(latest_execution.execution_id),
                "status": "cancelled",
                "message": "任务已成功取消"
            },
            message="任务执行已取消"
        )

    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="取消任务失败"
        )


@router.post("/{task_id}/execute-claude-code", response_model=APIResponse)
async def execute_task_with_claude_code(
    task_id: int,
    execution_context: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """使用Claude Code架构执行任务"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        # 使用新的Claude Code架构执行任务
        result = await task_service.execute_task_with_claude_code(
            db=db,
            task_id=task_id,
            user_id=user_id,
            execution_context=execution_context or {}
        )
        
        return APIResponse(
            success=True,
            data=result,
            message="Claude Code任务执行完成"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="Claude Code任务执行失败"
        )


@router.post("/sql/generate", response_model=APIResponse)
async def generate_sql_with_claude_code(
    query_description: str,
    table_info: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """使用Claude Code架构生成SQL"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        result = await task_service.generate_sql_with_claude_code(
            user_id=user_id,
            query_description=query_description,
            table_info=table_info or {}
        )
        
        return APIResponse(
            success=True,
            data=result,
            message="SQL生成完成"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="SQL生成失败"
        )


@router.post("/data/analyze", response_model=APIResponse)
async def analyze_data_with_claude_code(
    dataset: Dict[str, Any],
    analysis_type: str = "exploratory",
    current_user: User = Depends(get_current_user)
):
    """使用Claude Code架构分析数据"""
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        result = await task_service.analyze_data_with_claude_code(
            user_id=user_id,
            dataset=dataset,
            analysis_type=analysis_type
        )
        
        return APIResponse(
            success=True,
            data=result,
            message="数据分析完成"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="数据分析失败"
        )




@router.post("/{task_id}/run-report", response_model=APIResponse[Dict[str, Any]])
async def run_task_report_pipeline(
    task_id: int,
    request: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行任务报告流水线：占位符校验/修复 -> ETL -> 组装并生成DOCX。

    请求体（可选）:
    - execution_time: ISO时间，用作时间窗口参考
    - cron_expression: Cron表达式，不传则使用任务上的 schedule
    - force_repair: 是否强制重修复（默认False）
    - preview_only: 仅返回校验和ETL JSON，不生成docx（默认False）
    - output_format: 默认 docx
    """
    try:
        req = request or {}
        force_repair = bool(req.get("force_repair", False))
        preview_only = bool(req.get("preview_only", False))
        output_format = str(req.get("output_format", "docx")).lower()
        exec_time_str = req.get("execution_time")
        cron_expression = req.get("cron_expression")

        # 1) 加载任务/模板/数据源，校验权限
        user_id = current_user.id
        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或无权限")

        from app.models.template import Template
        from app.models.data_source import DataSource
        template = db.query(Template).filter(Template.id == task.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")

        # 2) 构建时间上下文（基于任务cron+执行时间）
        tcm = TimeContextManager()
        if not cron_expression:
            cron_expression = task.schedule
        exec_dt = None
        if exec_time_str:
            try:
                exec_dt = datetime.fromisoformat(exec_time_str.replace('Z', '+00:00'))
            except Exception:
                exec_dt = None
        time_ctx: Dict[str, Any] = {}
        if cron_expression:
            tc = tcm.build_task_time_context(cron_expression, exec_dt)
            time_ctx = {
                "cron_expression": cron_expression,
                "execution_time": (exec_dt.isoformat() if exec_dt else tc.get("execution_time")),
                "start_date": tc.get("data_start_time"),
                "end_date": tc.get("data_end_time"),
                "period_description": tc.get("period_description"),
            }
        else:
            # 无cron时，使用近7天窗口
            from datetime import timedelta as _td
            end = datetime.utcnow().date().isoformat()
            start = (datetime.utcnow().date() - _td(days=7)).isoformat()
            time_ctx = {"start_date": start, "end_date": end, "execution_time": (datetime.utcnow().isoformat())}

        # 3) 占位符校验/修复
        validation_service = create_placeholder_validation_service(str(user_id))
        ds_info = {"data_source_id": str(task.data_source_id), "name": data_source.name}
        validation_summary = await validation_service.batch_repair_template_placeholders(
            template_id=str(task.template_id),
            data_source_info=ds_info,
            time_context=time_ctx,
            force_repair=force_repair,
        )

        # 读取DB中当前占位符配置，以便ETL
        from app import crud as _crud
        placeholders = _crud.template_placeholder.get_by_template(db, template_id=str(task.template_id))

        # 所有占位符若均无效，则强制重修复/重新生成SQL
        total_ph = len(placeholders)
        if total_ph == 0:
            raise HTTPException(status_code=400, detail="模板未包含任何占位符")
        all_invalid = all((not p.generated_sql) or (not p.sql_validated) for p in placeholders)
        if all_invalid:
            validation_summary = await validation_service.batch_repair_template_placeholders(
                template_id=str(task.template_id),
                data_source_info=ds_info,
                time_context=time_ctx,
                force_repair=True,
            )
            # 重新加载占位符
            placeholders = _crud.template_placeholder.get_by_template(db, template_id=str(task.template_id))

        # 4) ETL：逐占位符执行SQL
        etl_results: Dict[str, Any] = {}
        etl_start = _time.time()
        for p in placeholders:
            if not getattr(p, 'is_active', True) or not p.generated_sql:
                continue
            q_start = _time.time()
            # 使用带占位符替换的执行方法，确保时间窗口被正确替换
            qres = await query_executor_service.execute_query_with_placeholders(
                p.generated_sql,
                time_ctx or {},
                {"data_source_id": str(task.data_source_id)}
            )
            etl_results[p.placeholder_name] = {
                "success": bool(qres.get("success")),
                "data": qres.get("data", []),
                "metadata": qres.get("metadata", {}),
                "execution_time_ms": int((qres.get("execution_time") or 0) * 1000),
                "columns": (qres.get("metadata", {}) or {}).get("columns", []),
                "row_count": (qres.get("metadata", {}) or {}).get("row_count", len(qres.get("data", []) or [])),
                "placeholder": {
                    "name": p.placeholder_name,
                    "type": p.placeholder_type,
                    "content_type": p.content_type,
                },
                "started_at": datetime.fromtimestamp(q_start).isoformat(),
                "finished_at": datetime.utcnow().isoformat(),
            }
        etl_duration_ms = int((_time.time() - etl_start) * 1000)

        # 5) 图表生成（简化：为content_type=chart生成基础柱状图）
        chart_results: List[Dict[str, Any]] = []
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            _os.makedirs(f"/tmp/charts/{user_id}", exist_ok=True)

            def _is_numeric_value(v):
                if isinstance(v, (int, float, Decimal)):
                    return True
                if isinstance(v, str):
                    try:
                        float(v.strip())
                        return True
                    except Exception:
                        return False
                return False

            def _sanitize_filename(name: str) -> str:
                safe = ''.join(ch if ch.isalnum() or ch in ('_', '-', '.') else '_' for ch in str(name))
                return safe[:100] if len(safe) > 100 else safe

            for p in placeholders:
                if str(getattr(p, 'content_type', '')).lower() != 'chart':
                    continue
                pres = etl_results.get(p.placeholder_name)
                if not pres or not pres.get("data"):
                    chart_results.append({
                        "success": False,
                        "chart_type": "bar",
                        "file_path": None,
                        "metadata": {"title": p.description or p.placeholder_name},
                        "error": "no_data"
                    })
                    continue
                rows = pres["data"]
                # 推断列
                columns = pres.get("columns") or (list(rows[0].keys()) if isinstance(rows[0], dict) else None)
                if not columns:
                    chart_results.append({
                        "success": False,
                        "chart_type": "bar",
                        "file_path": None,
                        "metadata": {"title": p.description or p.placeholder_name},
                        "error": "no_columns"
                    })
                    continue
                x_col = columns[0]
                y_col = None
                for c in columns[1:]:
                    try:
                        if any(_is_numeric_value(r.get(c)) for r in rows if isinstance(r, dict)):
                            y_col = c
                            break
                    except Exception:
                        continue
                if not y_col:
                    chart_results.append({
                        "success": False,
                        "chart_type": "bar",
                        "file_path": None,
                        "metadata": {"title": p.description or p.placeholder_name},
                        "error": "no_numeric_column"
                    })
                    continue

                # 构造绘图数据
                x_vals = [r.get(x_col) for r in rows if isinstance(r, dict)]
                y_vals = [r.get(y_col) for r in rows if isinstance(r, dict)]

                # 清洗与转换数值
                cleaned_y = []
                for v in y_vals:
                    if isinstance(v, (int, float, Decimal)):
                        cleaned_y.append(float(v))
                    elif isinstance(v, str):
                        try:
                            cleaned_y.append(float(v.strip()))
                        except Exception:
                            cleaned_y.append(float('nan'))
                    else:
                        cleaned_y.append(float('nan'))

                # 处理过多类目：保留前N（按值降序），默认N=20
                N = 20
                try:
                    pairs = list(zip(x_vals, cleaned_y))
                    pairs = [p2 for p2 in pairs if p2[0] is not None]
                    pairs.sort(key=lambda t: (t[1] if t[1] == t[1] else float('-inf')), reverse=True)
                    if len(pairs) > N:
                        pairs = pairs[:N]
                    x_vals_plot, y_vals_plot = zip(*pairs) if pairs else ([], [])
                except Exception:
                    x_vals_plot, y_vals_plot = x_vals[:N], cleaned_y[:N]

                # 若类目较多，切换为水平条形图
                use_barh = len(x_vals_plot) > 10

                plt.figure(figsize=(10, 6))
                try:
                    if use_barh:
                        plt.barh(list(map(lambda s: str(s)[:50], x_vals_plot)), y_vals_plot)
                    else:
                        plt.bar(list(map(lambda s: str(s)[:50], x_vals_plot)), y_vals_plot)
                    plt.title(p.description or p.placeholder_name)
                    if not use_barh:
                        plt.xticks(rotation=30, ha='right')
                    plt.tight_layout()
                    safe_name = _sanitize_filename(p.placeholder_name)
                    fname = f"/tmp/charts/{user_id}/chart_{safe_name}_{int(_time.time())}.png"
                    plt.savefig(fname, dpi=150)
                    chart_results.append({
                        "success": True,
                        "chart_type": "barh" if use_barh else "bar",
                        "file_path": fname,
                        "metadata": {
                            "title": p.description or p.placeholder_name,
                            "x_col": x_col,
                            "y_col": y_col,
                            "top_n": len(x_vals_plot)
                        }
                    })
                except Exception as _plot_err:
                    chart_results.append({
                        "success": False,
                        "chart_type": "bar",
                        "file_path": None,
                        "metadata": {"title": p.description or p.placeholder_name},
                        "error": str(_plot_err)
                    })
                finally:
                    plt.close()
        except Exception as _chart_block_err:
            # 不清空已有结果，仅记录块级错误
            chart_results.append({
                "success": False,
                "chart_type": "bar",
                "file_path": None,
                "metadata": {"title": "chart_block"},
                "error": str(_chart_block_err)
            })

        # 6) 生成用于文本占位符的直接替换值（优先原值，其次单句改写）
        direct_values: Dict[str, str] = {}
        end_for_sentence = time_ctx.get("end_date") or time_ctx.get("execution_time") or "本期"

        def _format_scalar(value: Any) -> str:
            try:
                # 数值格式：千分位，最多保留2位小数
                if isinstance(value, (int, float, Decimal)):
                    num = float(value)
                    if abs(num) >= 1000:
                        return f"{num:,.2f}".rstrip('0').rstrip('.')
                    return f"{num:.2f}".rstrip('0').rstrip('.')
                # 日期/时间格式
                if hasattr(value, 'isoformat'):
                    try:
                        return value.strftime('%Y-%m-%d')
                    except Exception:
                        return str(value)
                # 字符串：去除首尾空白并限制长度
                if isinstance(value, str):
                    s = value.strip()
                    return s if len(s) <= 120 else (s[:117] + '...')
                # 其它可序列化类型
                return str(value)
            except Exception:
                return str(value)

        for p in placeholders:
            # 跳过图表类占位符（由chart_results处理）
            if str(getattr(p, 'content_type', '')).lower() == 'chart':
                continue
            name = p.placeholder_name
            pres = etl_results.get(name)
            if not pres:
                # 无ETL结果，单句改写为提示
                direct_values[name] = f"{p.description or name}暂无可用数据"
                continue

            rows = pres.get("data") or []
            cols = pres.get("columns") or []
            # 优先原始标量值
            scalar_value = None
            try:
                if rows:
                    first = rows[0]
                    if isinstance(first, dict):
                        # 若仅一列，直接取该列
                        if len(cols) == 1 and cols[0] in first:
                            scalar_value = first.get(cols[0])
                        else:
                            # 找第一个数值列，否则第一个非空值
                            preferred = None
                            for c in cols:
                                v = first.get(c)
                                if isinstance(v, (int, float, Decimal)):
                                    preferred = v
                                    break
                            if preferred is not None:
                                scalar_value = preferred
                            else:
                                for c in cols:
                                    v = first.get(c)
                                    if v not in (None, ""):
                                        scalar_value = v
                                        break
                    elif isinstance(first, list) and first:
                        scalar_value = first[0]
            except Exception:
                scalar_value = None

            if scalar_value is not None:
                direct_values[name] = _format_scalar(scalar_value)
            else:
                # 单句改写（极简）：
                if not rows:
                    direct_values[name] = f"{p.description or name}在{end_for_sentence}无数据"
                else:
                    # 多行/无法提取标量时，取Top1摘要
                    if isinstance(rows[0], dict) and cols:
                        x = rows[0].get(cols[0])
                        y = None
                        for c in cols[1:]:
                            v = rows[0].get(c)
                            if isinstance(v, (int, float, Decimal)) or (isinstance(v, str) and v.strip()):
                                y = v
                                break
                        if y is not None:
                            direct_values[name] = f"{p.description or name}（{_format_scalar(x)}）：{_format_scalar(y)}"
                        else:
                            direct_values[name] = f"{p.description or name}（示例：{_format_scalar(x)}）"
                    else:
                        direct_values[name] = f"{p.description or name}数据已更新"

        # 7) 预览或生成文档
        payload = {
            "task": {"id": task.id, "name": task.name},
            "template": {"id": str(task.template_id), "name": getattr(template, 'name', '模板')},
            "time_context": time_ctx,
            "validation": validation_summary,
            "etl": {
                "placeholders": list(etl_results.keys()),
                "results": etl_results,
                "duration_ms": etl_duration_ms,
            },
            "charts": chart_results,
        }

        if preview_only:
            return APIResponse(success=True, data=payload, message="预览成功（未生成文档）")

        word_service = create_word_export_service(str(user_id))
        export_res = await word_service.export_report_document(
            template_id=str(task.template_id),
            placeholder_data={
                **(validation_summary if isinstance(validation_summary, dict) else {"validation_results": []}),
                "direct_values": direct_values,
            },
            etl_data={str(task.data_source_id): {"transform": {"success": True, "data": [v for v in etl_results.values()]}}},
            chart_data={"data": chart_results},
        )

        # 7.5) 💾 持久化 direct_values 和图表数据到 placeholder_values 表
        # 仅在文档生成成功后持久化
        if export_res.success:
            try:
                batch_id = ETLPersistenceService.generate_batch_id()
                values_to_save = []

                # 解析时间上下文
                execution_time = None
                period_start = None
                period_end = None
                try:
                    if time_ctx.get("execution_time"):
                        execution_time = datetime.fromisoformat(str(time_ctx["execution_time"]).replace("Z", "+00:00"))
                    if time_ctx.get("start_date"):
                        period_start = datetime.fromisoformat(str(time_ctx["start_date"]).replace("Z", "+00:00"))
                    if time_ctx.get("end_date"):
                        period_end = datetime.fromisoformat(str(time_ctx["end_date"]).replace("Z", "+00:00"))
                except Exception as time_parse_err:
                    logger.warning(f"⚠️ 解析时间上下文失败: {time_parse_err}")
                    execution_time = datetime.utcnow()

                # 持久化文本占位符（direct_values）
                for p in placeholders:
                    name = p.placeholder_name

                    # 跳过图表占位符，稍后单独处理
                    if str(getattr(p, 'content_type', '')).lower() == 'chart':
                        continue

                    # 只保存有 direct_values 的占位符
                    if name not in direct_values:
                        continue

                    etl_result = etl_results.get(name, {})

                    values_to_save.append(PlaceholderValueCreate(
                        placeholder_id=p.id,
                        data_source_id=task.data_source_id,
                        # 🔑 核心：使用精细格式化的 formatted_text
                        formatted_text=direct_values[name],
                        raw_query_result=etl_result.get("data"),
                        processed_value={
                            "columns": etl_result.get("columns", []),
                            "row_count": len(etl_result.get("data", [])),
                            "metadata": etl_result.get("metadata", {})
                        },
                        execution_sql=p.generated_sql,
                        row_count=len(etl_result.get("data", [])),
                        success=True,
                        source="run_report",
                        confidence_score=1.0,
                        analysis_metadata={
                            "content_type": str(getattr(p, 'content_type', 'text')),
                            "placeholder_type": str(getattr(p, 'placeholder_type', 'unknown')),
                            "formatting_applied": "千分位,小数精度,智能改写"
                        },
                        execution_time=execution_time or datetime.utcnow(),
                        period_start=period_start,
                        period_end=period_end,
                        report_period=time_ctx.get("report_period"),
                        sql_parameters_snapshot=time_ctx,
                        execution_batch_id=batch_id,
                        is_latest_version=True,
                        cache_key=f"ph_{p.id}_{time_ctx.get('start_date', 'default')}",
                        expires_at=datetime.utcnow() + timedelta(hours=getattr(p, 'cache_ttl_hours', 24))
                    ))

                # 持久化图表占位符
                for chart_result in chart_results:
                    if not chart_result.get("success"):
                        continue

                    chart_name = chart_result.get("placeholder_name")
                    if not chart_name:
                        continue

                    # 找到对应的占位符
                    chart_placeholder = next((p for p in placeholders if p.placeholder_name == chart_name), None)
                    if not chart_placeholder:
                        continue

                    etl_result = etl_results.get(chart_name, {})
                    chart_metadata = chart_result.get("metadata", {})

                    values_to_save.append(PlaceholderValueCreate(
                        placeholder_id=chart_placeholder.id,
                        data_source_id=task.data_source_id,
                        # 图表的 formatted_text 记录关键信息
                        formatted_text=f"图表：{chart_metadata.get('title', chart_name)} | "
                                      f"X轴：{chart_metadata.get('x_column')} | "
                                      f"Y轴：{chart_metadata.get('y_column')} | "
                                      f"Top-{chart_metadata.get('top_n', 'All')}",
                        raw_query_result=etl_result.get("data"),
                        processed_value={
                            "chart_type": chart_metadata.get("chart_type"),
                            "file_path": chart_result.get("file_path"),
                            "columns": etl_result.get("columns", []),
                            "row_count": len(etl_result.get("data", [])),
                            "chart_metadata": chart_metadata
                        },
                        execution_sql=chart_placeholder.generated_sql,
                        row_count=len(etl_result.get("data", [])),
                        success=True,
                        source="run_report_chart",
                        confidence_score=1.0,
                        analysis_metadata={
                            "content_type": "chart",
                            "chart_generated": True,
                            "chart_path": chart_result.get("file_path"),
                            **chart_metadata
                        },
                        execution_time=execution_time or datetime.utcnow(),
                        period_start=period_start,
                        period_end=period_end,
                        report_period=time_ctx.get("report_period"),
                        sql_parameters_snapshot=time_ctx,
                        execution_batch_id=batch_id,
                        is_latest_version=True,
                        cache_key=f"ph_{chart_placeholder.id}_{time_ctx.get('start_date', 'default')}",
                        expires_at=datetime.utcnow() + timedelta(hours=getattr(chart_placeholder, 'cache_ttl_hours', 24))
                    ))

                # 🔑 批量插入数据库
                if values_to_save:
                    crud.placeholder_value.create_batch(db, values=values_to_save)
                    db.commit()
                    logger.info(f"✅ 已持久化 {len(values_to_save)} 个占位符值到数据库 (batch_id={batch_id})")
                else:
                    logger.warning("⚠️ 没有需要持久化的占位符值")

            except Exception as persist_err:
                logger.error(f"❌ 持久化占位符值失败: {persist_err}")
                logger.exception(persist_err)
                # 持久化失败不影响主流程，继续执行
                db.rollback()

        payload["document"] = {
            "success": export_res.success,
            "document_path": export_res.document_path,
            "file_size_bytes": export_res.file_size_bytes,
            "page_count": export_res.page_count,
            "export_time_seconds": export_res.export_time_seconds,
            "error": export_res.error,
            "meta": export_res.metadata,
        }

        return APIResponse(
            success=bool(export_res.success),
            data=payload,
            message=("报告生成成功" if export_res.success else (export_res.error or "报告生成失败"))
        )

    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            errors=[str(e)],
            message="运行报告流水线失败"
        )
