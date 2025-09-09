from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.application.task_application_service import TaskApplicationService
from app.services.infrastructure.task_queue.celery_config import celery_app

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
    
    # 转换为TaskResponse格式，保持向后兼容
    task_dicts = []
    for task in tasks:
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
            
            # 新增字段（可选，有默认值，保持前端兼容）
            "status": task.status.value if hasattr(task, 'status') and task.status else "pending",
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
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        task = task_service.create_task(
            db=db,
            user_id=user_id,
            name=task_in.name,
            template_id=str(task_in.template_id),
            data_source_id=str(task_in.data_source_id),
            report_period=task_in.report_period,
            description=task_in.description,
            schedule=task_in.schedule,
            recipients=task_in.recipients,
            is_active=task_in.is_active
        )
        
        task_schema = TaskResponse.model_validate(task)
        task_dict = task_schema.model_dump()
        return ApiResponse(
            success=True,
            data=task_dict,
            message="任务创建成功"
        )
    except Exception as e:
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
        return ApiResponse(
            success=True,
            data=task_dict,
            message="任务更新成功"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务更新失败"
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
    try:
        task_service = TaskApplicationService()
        user_id = str(current_user.id)
        
        success = task_service.delete_task(
            db=db,
            task_id=task_id,
            user_id=user_id
        )
        
        return ApiResponse(
            success=True,
            data={"task_id": task_id, "deleted": success},
            message="任务删除成功"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务删除失败"
        )


@router.post("/{task_id}/execute", response_model=ApiResponse)
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
        
        return ApiResponse(
            success=True,
            data=result,
            message="任务执行请求已提交"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务执行失败"
        )


@router.post("/{task_id}/run", response_model=ApiResponse)
async def run_task(
    task_id: int,
    execution_time: Optional[str] = Query(None, description="任务执行时间 (YYYY-MM-DD HH:MM:SS，默认为当前时间)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行任务 - /execute 接口的别名，提供更直观的接口"""
    # 直接调用 execute_task 函数，复用相同的逻辑
    return await execute_task(task_id, execution_time, db, current_user)


@router.get("/{task_id}/executions", response_model=ApiResponse)
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
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "executions": executions
            },
            message="获取执行历史成功"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取执行历史失败"
        )


@router.post("/{task_id}/validate", response_model=ApiResponse)
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
        
        return ApiResponse(
            success=True,
            data=validation_result,
            message="任务配置验证已启动"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务配置验证失败"
        )


@router.post("/{task_id}/schedule", response_model=ApiResponse)
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
        
        return ApiResponse(
            success=True,
            data=result,
            message="任务调度设置成功"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务调度设置失败"
        )


@router.get("/{task_id}/status", response_model=ApiResponse)
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
        
        return ApiResponse(
            success=True,
            data=status_data,
            message="获取任务状态成功"
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取任务状态失败"
        )




