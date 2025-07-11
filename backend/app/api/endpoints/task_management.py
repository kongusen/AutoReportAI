from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.get("", response_model=List[schemas.Task])
def list_tasks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Lists all scheduled report generation tasks from the database.
    """
    tasks = crud.task.get_multi(db, skip=skip, limit=limit)
    return tasks

@router.post("", response_model=schemas.Task)
def create_task(
    *,
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
):
    """
    Creates a new scheduled task in the database.
    """
    task = crud.task.create(db=db, obj_in=task_in)
    return task

@router.put("/{task_id}", response_model=schemas.Task)
def update_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    task_in: schemas.TaskUpdate,
):
    """
    Updates an existing scheduled task in the database.
    """
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task = crud.task.update(db=db, db_obj=task, obj_in=task_in)
    return task
