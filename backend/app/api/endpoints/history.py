from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.ReportHistory])
def read_report_history(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve report history.
    """
    if crud.user.is_superuser(current_user):
        # Superusers can see all history
        history = crud.report_history.get_multi(db, skip=skip, limit=limit)
    else:
        # Regular users can only see history for their own tasks
        history = crud.report_history.get_multi_by_owner(
            db=db, owner_id=current_user.id, skip=skip, limit=limit
        )
    return history


@router.get("/{history_id}", response_model=schemas.ReportHistory)
def read_report_history_item(
    *,
    db: Session = Depends(deps.get_db),
    history_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get specific report history item by ID.
    """
    history_item = crud.report_history.get(db=db, id=history_id)
    if not history_item:
        raise HTTPException(status_code=404, detail="Report history not found")
    
    # Check permissions - users can only see history for their own tasks
    if not crud.user.is_superuser(current_user):
        task = crud.task.get(db=db, id=history_item.task_id)
        if not task or task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return history_item


@router.get("/task/{task_id}", response_model=List[schemas.ReportHistory])
def read_task_history(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get report history for a specific task.
    """
    # Check if task exists and user has permission
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not crud.user.is_superuser(current_user) and task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get history for this task
    history = crud.report_history.get_by_task_id(db=db, task_id=task_id)
    return history 