"""认证相关API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.architecture import ApiResponse
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User as ORMUser
from app.schemas.user import UserCreate, UserSchema
from app.schemas.token import Token
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    from app.crud.crud_user import user as crud_user
    
    # 检查邮箱是否已存在
    if crud_user.get_by_email(db, email=user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 检查用户名是否已存在
    if user_data.username and crud_user.get_by_username(db, username=user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被使用"
        )
    
    # 创建用户
    user_obj = crud_user.create(db, obj_in=user_data)
    user_schema = UserSchema.model_validate(user_obj)
    user_dict = user_schema.model_dump()
    user_dict['unique_id'] = str(user_dict.get('id'))
    return {"id": user_dict["id"], "user": user_dict}


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    from app.crud.crud_user import user as crud_user
    # 验证用户
    user_obj = crud_user.authenticate(
        db, 
        username=form_data.username, 
        password=form_data.password
    )
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    # 创建访问令牌
    access_token = create_access_token(str(user_obj.id))
    user_schema = UserSchema.model_validate(user_obj)
    user_dict = user_schema.model_dump()
    user_dict['unique_id'] = str(user_dict.get('id'))
    return {"access_token": access_token, "token_type": "bearer", "user": user_dict}


@router.post("/logout")
async def logout(
    current_user: ORMUser = Depends(get_current_user)
):
    """用户登出"""
    # 在实际应用中，这里可以处理令牌撤销
    return ApiResponse(
        success=True,
        message="登出成功"
    )


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: ORMUser = Depends(get_current_user)):
    """获取当前用户信息"""
    user_id = current_user.id
    if not isinstance(user_id, UUID):
        user_id = UUID(str(user_id))
    current_user.id = user_id
    return current_user


@router.post("/refresh")
async def refresh_token(
    current_user: ORMUser = Depends(get_current_user)
):
    """刷新访问令牌"""
    access_token = create_access_token(
        data={"sub": str(current_user.id)}
    )
    
    return ApiResponse(
        success=True,
        data={"access_token": access_token, "token_type": "bearer"},
        message="令牌刷新成功"
    )


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """请求密码重置"""
    from app.crud.crud_user import user as crud_user
    
    user_obj = crud_user.get_by_email(db, email=email)
    if not user_obj:
        # 为了安全，即使用户不存在也返回成功
        return ApiResponse(
            success=True,
            message="如果该邮箱存在，我们已发送密码重置链接"
        )
    
    # TODO: 实现邮件发送功能
    # 这里应该生成重置令牌并发送邮件
    
    return ApiResponse(
        success=True,
        message="如果该邮箱存在，我们已发送密码重置链接"
    )


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """重置密码"""
    # TODO: 验证重置令牌
    # 这里应该验证令牌的有效性并重置密码
    
    return ApiResponse(
        success=True,
        message="密码重置成功"
    )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: ORMUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    from app.crud.crud_user import user as crud_user
    
    # 验证当前密码
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 更新密码
    crud_user.update_password(db, user_id=current_user.id, new_password=new_password)
    
    return ApiResponse(
        success=True,
        message="密码修改成功"
    )
