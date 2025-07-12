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
