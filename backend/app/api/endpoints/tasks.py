from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.crud.crud_task import crud_task
from app.core.worker import celery_app

router = APIRouter()


@router.get("/", response_model=ApiResponse)
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
    query = db.query(Task).filter(Task.owner_id == user_id)
    
    if is_active is not None:
        query = query.filter(Task.is_active == is_active)
    
    if search:
        query = query.filter(Task.name.contains(search))
    
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    
    # 手动转换数据以避免schema验证问题
    task_dicts = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "template_id": str(task.template_id) if task.template_id else None,
            "data_source_id": str(task.data_source_id) if task.data_source_id else None,
            "schedule": task.schedule,
            "recipients": task.recipients or [],
            "owner_id": str(task.owner_id) if task.owner_id else None,
            "is_active": task.is_active,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "unique_id": str(task.id)
        }
        task_dicts.append(task_dict)
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=task_dicts,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", response_model=ApiResponse)
async def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建任务"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        task = crud_task.create_with_user(db, obj_in=task_in, user_id=user_id)
        task_schema = TaskResponse.model_validate(task)
        task_dict = task_schema.model_dump()
        return ApiResponse(
            success=True,
            data=task_dict,
            message="任务创建成功"
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务创建失败"
        )


@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = crud_task.update(db, db_obj=task, obj_in=task_in)
    task_schema = TaskResponse.model_validate(task)
    task_dict = task_schema.model_dump()
    return ApiResponse(
        success=True,
        data=task_dict,
        message="任务更新成功"
    )


@router.get("/{task_id}", response_model=ApiResponse)
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
    return ApiResponse(
        success=True,
        data=task_dict,
        message="获取任务成功"
    )


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    crud_task.remove(db, id=task_id)
    return ApiResponse(
        success=True,
        data={"task_id": task_id},
        message="任务删除成功"
    )


@router.post("/{task_id}/execute", response_model=ApiResponse)
async def execute_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行任务 - 统一使用智能占位符驱动的流水线"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    # 发送一个Celery任务来异步执行智能报告生成
    try:
        # 在Redis中保存任务所有者信息以便进度通知
        from app.core.config import settings
        import redis.asyncio as redis
        
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        import asyncio
        asyncio.create_task(redis_client.set(f"report_task:{task.id}:owner", str(user_id), ex=3600))
        
        # 统一使用智能占位符驱动的报告生成流水线
        task_result = celery_app.send_task(
            "app.core.worker.intelligent_report_generation_pipeline", 
            args=[task.id, str(user_id)]
        )
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "celery_task_id": str(task_result.id),
                "status": "queued",
                "processing_mode": "intelligent"
            },
            message="智能占位符报告生成任务已加入队列"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务执行失败"
        )


@router.get("/{task_id}/status", response_model=ApiResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务执行状态"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")
    
    # 从Redis获取任务状态
    import redis.asyncio as redis
    from app.core.config import settings
    
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        status_data = await redis_client.hgetall(f"report_task:{task_id}:status")
        if not status_data:
            status_data = {"status": "not_started", "progress": 0}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取任务状态失败: {e}")
        status_data = {"status": "unknown", "progress": 0}
    finally:
        await redis_client.close()
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "task_name": task.name,
            **status_data
        },
        message="获取任务状态成功"
    )
