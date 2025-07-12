from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.TaskRead])
def read_tasks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tasks.
    """
    if crud.user.is_superuser(current_user):
        tasks = crud.task.get_multi(db, skip=skip, limit=limit)
    else:
        tasks = crud.task.get_multi_by_owner(
            db=db, owner_id=current_user.id, skip=skip, limit=limit
        )
    return tasks


@router.post("/", response_model=schemas.TaskRead)
def create_task(
    *,
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new task.
    """
    # Verify data source exists
    data_source = crud.data_source.get(db=db, id=task_in.data_source_id)
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Verify template exists
    template = crud.template.get(db=db, id=task_in.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    task = crud.task.create(db=db, obj_in=task_in, owner_id=current_user.id)
    return task


@router.get("/{task_id}", response_model=schemas.TaskRead)
def read_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get task by ID.
    """
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if not crud.user.is_superuser(current_user) and task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return task


@router.put("/{task_id}", response_model=schemas.TaskRead)
def update_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    task_in: schemas.TaskUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a task.
    """
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if not crud.user.is_superuser(current_user) and task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Verify data source exists if being updated
    if task_in.data_source_id and task_in.data_source_id != task.data_source_id:
        data_source = crud.data_source.get(db=db, id=task_in.data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="Data source not found")
    
    # Verify template exists if being updated
    if task_in.template_id and task_in.template_id != task.template_id:
        template = crud.template.get(db=db, id=task_in.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
    
    task = crud.task.update(db=db, db_obj=task, obj_in=task_in)
    return task


@router.delete("/{task_id}", response_model=schemas.Msg)
def delete_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a task.
    """
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if not crud.user.is_superuser(current_user) and task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    crud.task.remove(db=db, id=task_id)
    return {"msg": "Task deleted successfully"}
