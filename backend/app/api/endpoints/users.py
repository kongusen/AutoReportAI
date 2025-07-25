"""用户管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, User
from app.crud.crud_user import user as crud_user
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.READ))
):
    """获取用户列表（管理员功能）"""
    query = db.query(User)
    
    if search:
        query = query.filter(
            User.email.contains(search) | 
            User.username.contains(search) |
            User.full_name.contains(search)
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=users,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.get("/me", response_model=ApiResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return ApiResponse(
        success=True,
        data=current_user,
        message="获取用户信息成功"
    )


@router.get("/{user_id}", response_model=ApiResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.READ))
):
    """获取特定用户信息"""
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=422, detail="用户ID格式错误")
    user = crud_user.get(db, id=user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return ApiResponse(
        success=True,
        data=user,
        message="获取用户信息成功"
    )


@router.put("/me", response_model=ApiResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前用户信息"""
    user = crud_user.update(db, db_obj=current_user, obj_in=user_update)
    
    return ApiResponse(
        success=True,
        data=user,
        message="用户信息更新成功"
    )


@router.put("/{user_id}", response_model=ApiResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """更新用户信息（管理员功能）"""
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=422, detail="用户ID格式错误")
    user = crud_user.get(db, id=user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user = crud_user.update(db, db_obj=user, obj_in=user_update)
    
    return ApiResponse(
        success=True,
        data=user,
        message="用户信息更新成功"
    )


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """删除用户（管理员功能）"""
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=422, detail="用户ID格式错误")
    user = crud_user.get(db, id=user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    crud_user.remove(db, id=user_uuid)
    
    return ApiResponse(
        success=True,
        data={"user_id": user_id},
        message="用户删除成功"
    )


@router.post("/{user_id}/activate", response_model=ApiResponse)
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """激活用户（管理员功能）"""
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=422, detail="用户ID格式错误")
    user = crud_user.get(db, id=user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user = crud_user.update(db, db_obj=user, obj_in={"is_active": True})
    
    return ApiResponse(
        success=True,
        data=user,
        message="用户激活成功"
    )


@router.post("/{user_id}/deactivate", response_model=ApiResponse)
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(ResourceType.USER, PermissionLevel.ADMIN))
):
    """禁用用户（管理员功能）"""
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=422, detail="用户ID格式错误")
    user = crud_user.get(db, id=user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user = crud_user.update(db, db_obj=user, obj_in={"is_active": False})
    
    return ApiResponse(
        success=True,
        data=user,
        message="用户停用成功"
    )
