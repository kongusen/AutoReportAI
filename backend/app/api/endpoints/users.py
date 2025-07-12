from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps

router = APIRouter()


@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get current user.
    """
    return current_user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
):
    """
    Get a specific user by id.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
