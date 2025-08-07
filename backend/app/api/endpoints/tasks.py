from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.worker import celery_app

router = APIRouter()


@router.get("/", response_model=List[schemas.Task])
def read_tasks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tasks.
    """
    tasks = crud.task.get_multi(db=db, skip=skip, limit=limit, user_id=current_user.id)
    return tasks


@router.post("/", response_model=schemas.Task)
def create_task(
    *, 
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new task.
    """
    task = crud.task.create_with_owner(db=db, obj_in=task_in, user_id=current_user.id)
    return task


@router.put("/{id}", response_model=schemas.Task)
def update_task(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    task_in: schemas.TaskUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a task.
    """
    task = crud.task.get(db=db, id=id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task = crud.task.update(db=db, db_obj=task, obj_in=task_in)
    return task


@router.get("/{id}", response_model=schemas.Task)
def read_task(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get task by ID.
    """
    task = crud.task.get(db=db, id=id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return task


@router.delete("/{id}", response_model=schemas.Task)
def delete_task(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a task.
    """
    task = crud.task.get(db=db, id=id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task = crud.task.remove(db=db, id=id)
    return task


@router.post("/{task_id}/run", response_model=schemas.Msg)
def run_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Run a specific task by ID.
    """
    task = crud.task.get_for_user(db=db, id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    # 发送一个Celery任务来异步执行报告生成
    task_result = celery_app.send_task(
        "app.core.worker.generate_report_task", args=[task.id]
    )

    return {"msg": f"报告生成任务已加入队列，Celery任务ID是: {task_result.id}"}
