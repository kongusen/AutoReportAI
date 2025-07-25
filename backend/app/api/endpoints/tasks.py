"""任务管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task as TaskModel
from app.schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema
from app.crud.crud_task import task as crud_task

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_tasks(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    template_id: Optional[str] = Query(None, description="模板ID"),
    data_source_id: Optional[int] = Query(None, description="数据源ID"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    query = db.query(TaskModel).filter(TaskModel.owner_id == user_id)
    
    if template_id:
        query = query.filter(TaskModel.template_id == template_id)
    
    if data_source_id:
        query = query.filter(TaskModel.data_source_id == data_source_id)
    
    if is_active is not None:
        query = query.filter(TaskModel.is_active == is_active)
    
    if search:
        query = query.filter(TaskModel.name.contains(search))
    
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    task_schemas = [TaskSchema.model_validate(t) for t in tasks]
    task_dicts = [ts.model_dump() | {"unique_id": str(ts.id), "task_id": str(ts.id)} for ts in task_schemas]
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


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建任务"""
    task_obj = crud_task.create_with_owner(
        db, 
        obj_in=task, 
        owner_id=current_user.id
    )
    task_schema = TaskSchema.model_validate(task_obj)
    task_dict = task_schema.model_dump()
    task_dict['unique_id'] = str(task_dict.get('id'))
    task_dict['task_id'] = str(task_dict.get('id'))
    return {"id": task_dict["id"], **task_dict}


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    task_schema = TaskSchema.model_validate(task)
    task_dict = task_schema.model_dump()
    task_dict['unique_id'] = str(task_dict.get('id'))
    task_dict['task_id'] = str(task_dict.get('id'))
    return ApiResponse(
        success=True,
        data=task_dict,
        message="获取任务成功"
    )


@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    task = crud_task.update(
        db, 
        db_obj=task, 
        obj_in=task_update
    )
    
    return ApiResponse(
        success=True,
        data=task,
        message="任务更新成功"
    )


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    crud_task.remove(db, id=task_id)
    
    return ApiResponse(
        success=True,
        data={"task_id": task_id},
        message="任务删除成功"
    )


@router.post("/{task_id}/run", response_model=ApiResponse)
async def run_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    # 在后台运行任务
    background_tasks.add_task(
        run_task_job,
        task_id=task_id
    )
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "status": "running",
            "message": "任务已开始运行"
        },
        message="任务已开始运行"
    )


@router.post("/{task_id}/enable", response_model=ApiResponse)
async def enable_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启用任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    task.is_active = True
    db.commit()
    db.refresh(task)
    
    return ApiResponse(
        success=True,
        data=task,
        message="任务已启用"
    )


@router.post("/{task_id}/disable", response_model=ApiResponse)
async def disable_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """禁用任务"""
    task = crud_task.get(db, id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    task.is_active = False
    db.commit()
    db.refresh(task)
    
    return ApiResponse(
        success=True,
        data=task,
        message="任务已禁用"
    )


async def run_task_job(task_id: int):
    """后台运行任务"""
    # 这里应该实现实际的任务运行逻辑
    pass
