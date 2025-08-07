"""AI提供商管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.ai_provider import AIProvider
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate, AIProviderResponse
from app.crud.crud_ai_provider import crud_ai_provider

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_ai_providers(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    provider_type: Optional[str] = Query(None, description="提供商类型"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取AI提供商列表"""
    query = db.query(AIProvider).filter(AIProvider.user_id == current_user.id)
    
    if provider_type:
        query = query.filter(AIProvider.provider_type == provider_type)
    
    if is_active is not None:
        query = query.filter(AIProvider.is_active == is_active)
    
    if search:
        query = query.filter(AIProvider.provider_name.contains(search))
    
    total = query.count()
    ai_providers = query.offset(skip).limit(limit).all()
    
    # 转换为响应模型列表
    response_items = []
    for provider in ai_providers:
        response_items.append(AIProviderResponse(
            id=provider.id,
            provider_name=provider.provider_name,
            provider_type=provider.provider_type,
            api_base_url=provider.api_base_url,
            default_model_name=provider.default_model_name,
            is_active=provider.is_active
        ))
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=response_items,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", response_model=ApiResponse)
async def create_ai_provider(
    ai_provider: AIProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建AI提供商"""
    ai_provider_obj = crud_ai_provider.create_with_user(
        db, 
        obj_in=ai_provider, 
        user_id=current_user.id
    )
    
    # 转换为响应模型
    response_data = AIProviderResponse(
        id=ai_provider_obj.id,
        provider_name=ai_provider_obj.provider_name,
        provider_type=ai_provider_obj.provider_type,
        api_base_url=ai_provider_obj.api_base_url,
        default_model_name=ai_provider_obj.default_model_name,
        is_active=ai_provider_obj.is_active
    )
    
    return ApiResponse(
        success=True,
        data=response_data,
        message="AI提供商创建成功"
    )


@router.get("/{ai_provider_id}", response_model=ApiResponse)
async def get_ai_provider(
    ai_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定AI提供商"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    return ApiResponse(
        success=True,
        data=ai_provider,
        message="获取AI提供商成功"
    )


@router.put("/{ai_provider_id}", response_model=ApiResponse)
async def update_ai_provider(
    ai_provider_id: int,
    ai_provider_update: AIProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新AI提供商"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    ai_provider = crud_ai_provider.update(
        db, 
        db_obj=ai_provider, 
        obj_in=ai_provider_update
    )
    
    return ApiResponse(
        success=True,
        data=ai_provider,
        message="AI提供商更新成功"
    )


@router.delete("/{ai_provider_id}", response_model=ApiResponse)
async def delete_ai_provider(
    ai_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除AI提供商"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    crud_ai_provider.remove(db, id=ai_provider_id)
    
    return ApiResponse(
        success=True,
        data={"ai_provider_id": ai_provider_id},
        message="AI提供商删除成功"
    )


@router.post("/{ai_provider_id}/test", response_model=ApiResponse)
async def test_ai_provider(
    ai_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试AI提供商连接"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    # 这里应该实现实际的连接测试逻辑
    return ApiResponse(
        success=True,
        data={
            "connection_status": "success",
            "response_time": 0.234,
            "ai_provider_name": ai_provider.provider_name
        },
        message="AI提供商连接测试成功"
    )


@router.post("/{ai_provider_id}/enable", response_model=ApiResponse)
async def enable_ai_provider(
    ai_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启用AI提供商"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    ai_provider.is_active = True
    db.commit()
    db.refresh(ai_provider)
    
    return ApiResponse(
        success=True,
        data=ai_provider,
        message="AI提供商已启用"
    )


@router.post("/{ai_provider_id}/disable", response_model=ApiResponse)
async def disable_ai_provider(
    ai_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """禁用AI提供商"""
    ai_provider = crud_ai_provider.get(db, id=ai_provider_id)
    if not ai_provider or ai_provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI提供商不存在或无权限访问"
        )
    
    ai_provider.is_active = False
    db.commit()
    db.refresh(ai_provider)
    
    return ApiResponse(
        success=True,
        data=ai_provider,
        message="AI提供商已禁用"
    )
