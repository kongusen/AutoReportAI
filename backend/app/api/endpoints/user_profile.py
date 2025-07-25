from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from uuid import UUID
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app import crud, schemas

router = APIRouter()

@router.get("/user-profile/me", response_model=schemas.UserProfile)
async def read_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    profile = crud.user_profile.get_or_create(db, user_id=user_id)
    return profile

@router.put("/user-profile/me", response_model=schemas.UserProfile)
async def update_user_profile(
    profile_in: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    profile = crud.user_profile.get_by_user_id(db, user_id=user_id)
    if not profile:
        profile = crud.user_profile.create(db, obj_in=profile_in, user_id=user_id)
    else:
        profile = crud.user_profile.update(db, db_obj=profile, obj_in=profile_in)
    return profile

@router.post("/user-profile/me", response_model=schemas.UserProfile)
async def create_user_profile(
    profile_in: schemas.UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    profile = crud.user_profile.get_by_user_id(db, user_id=user_id)
    if profile:
        raise HTTPException(status_code=400, detail="User profile already exists")
    profile = crud.user_profile.create(db, obj_in=profile_in, user_id=user_id)
    return profile 