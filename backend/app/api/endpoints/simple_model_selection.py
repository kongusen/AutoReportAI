"""
简化模型选择API端点
提供基于模型特性的实用选择接口
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.core.architecture import ApiResponse
from app.services.infrastructure.llm.simple_model_selector import (
    get_simple_model_selector,
    TaskRequirement,
    ModelSelection
)

router = APIRouter()


class TaskRequest(BaseModel):
    """任务请求"""
    requires_thinking: bool = False
    cost_sensitive: bool = False  
    speed_priority: bool = False


class ModelSelectionResponse(BaseModel):
    """模型选择响应"""
    model_id: int
    model_name: str
    model_type: str
    server_id: int
    server_name: str
    provider_type: str
    reasoning: str
    fallback_model_id: Optional[int] = None


@router.post("/select", response_model=ModelSelectionResponse)
async def select_model(
    *,
    db: Session = Depends(deps.get_db),
    task_request: TaskRequest,
    current_user = Depends(deps.get_current_active_user)
):
    """为当前用户选择最适合的模型"""
    
    try:
        # 转换任务需求
        task_requirement = TaskRequirement(
            requires_thinking=task_request.requires_thinking,
            cost_sensitive=task_request.cost_sensitive,
            speed_priority=task_request.speed_priority
        )
        
        # 获取选择器并进行选择
        selector = get_simple_model_selector()
        selection = selector.select_model_for_user(
            user_id=str(current_user.id),
            task_requirement=task_requirement,
            db=db
        )
        
        if not selection:
            raise HTTPException(
                status_code=404,
                detail="未找到可用的模型，请检查模型配置"
            )
        
        return ModelSelectionResponse(
            model_id=selection.model_id,
            model_name=selection.model_name,
            model_type=selection.model_type.value,
            server_id=selection.server_id,
            server_name=selection.server_name,
            provider_type=selection.provider_type,
            reasoning=selection.reasoning,
            fallback_model_id=selection.fallback_model_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"模型选择失败: {str(e)}"
        )


@router.get("/stats", response_model=ApiResponse)
async def get_user_model_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取当前用户的模型配置统计"""
    
    try:
        selector = get_simple_model_selector()
        stats = selector.get_user_model_stats(
            user_id=str(current_user.id),
            db=db
        )
        
        return ApiResponse(
            success=True,
            data={
                "user_id": str(current_user.id),
                "stats": stats
            },
            message="获取用户模型统计成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/available-types", response_model=ApiResponse)
async def get_available_model_types(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取用户可用的模型类型"""
    
    try:
        selector = get_simple_model_selector()
        stats = selector.get_user_model_stats(
            user_id=str(current_user.id),
            db=db
        )
        
        available_types = []
        if stats["default_models"] > 0:
            available_types.append({
                "type": "default",
                "name": "默认模型",
                "description": "适合常规对话和问答任务",
                "count": stats["default_models"]
            })
        
        if stats["think_models"] > 0:
            available_types.append({
                "type": "think", 
                "name": "思考模型",
                "description": "适合需要深度推理的复杂任务",
                "count": stats["think_models"]
            })
        
        return ApiResponse(
            success=True,
            data={
                "available_types": available_types,
                "total_models": stats["total_models"],
                "servers_count": stats["servers_count"]
            },
            message="获取可用模型类型成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取可用类型失败: {str(e)}"
        )