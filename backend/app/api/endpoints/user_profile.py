from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/me", response_model=schemas.UserProfile)
def read_user_profile(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """获取当前用户的配置"""
    profile = crud.user_profile.get_or_create(db, user_id=current_user.id)
    return profile


@router.put("/me", response_model=schemas.UserProfile)
def update_user_profile(
    *,
    db: Session = Depends(deps.get_db),
    profile_in: schemas.UserProfileUpdate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """更新当前用户的配置"""
    profile = crud.user_profile.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        profile = crud.user_profile.create(
            db, obj_in=profile_in, user_id=current_user.id
        )
    else:
        profile = crud.user_profile.update(db, db_obj=profile, obj_in=profile_in)
    return profile


@router.post("/me", response_model=schemas.UserProfile)
def create_user_profile(
    *,
    db: Session = Depends(deps.get_db),
    profile_in: schemas.UserProfileCreate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """创建当前用户的配置"""
    profile = crud.user_profile.get_by_user_id(db, user_id=current_user.id)
    if profile:
        raise HTTPException(status_code=400, detail="User profile already exists")
    profile = crud.user_profile.create(db, obj_in=profile_in, user_id=current_user.id)
    return profile
