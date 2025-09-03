"""
模型执行API端点
提供基于用户配置的实际模型调用接口
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.services.infrastructure.ai.llm.model_executor import get_model_executor
from app.services.infrastructure.ai.llm.simple_model_selector import TaskRequirement

router = APIRouter()


class ExecuteRequest(BaseModel):
    """执行请求"""
    prompt: str
    requires_thinking: bool = False
    cost_sensitive: bool = False
    speed_priority: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ExecuteWithModelRequest(BaseModel):
    """指定模型执行请求"""
    model_id: int
    prompt: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ExecutionResponse(BaseModel):
    """执行响应"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    selected_model: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    used_fallback: Optional[bool] = None


@router.post("/execute", response_model=ExecutionResponse)
async def execute_with_auto_selection(
    *,
    db: Session = Depends(deps.get_db),
    request: ExecuteRequest,
    current_user = Depends(deps.get_current_active_user)
):
    """基于任务需求自动选择模型并执行"""
    
    try:
        # 构建任务需求
        task_requirement = TaskRequirement(
            requires_thinking=request.requires_thinking,
            cost_sensitive=request.cost_sensitive,
            speed_priority=request.speed_priority
        )
        
        # 构建执行参数
        exec_kwargs = {}
        if request.temperature is not None:
            exec_kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            exec_kwargs["max_tokens"] = request.max_tokens
        
        # 执行模型调用
        executor = get_model_executor()
        result = await executor.execute_with_auto_selection(
            user_id=str(current_user.id),
            prompt=request.prompt,
            task_requirement=task_requirement,
            db=db,
            **exec_kwargs
        )
        
        return ExecutionResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"模型执行失败: {str(e)}"
        )


@router.post("/execute-with-model", response_model=ExecutionResponse)
async def execute_with_specific_model(
    *,
    db: Session = Depends(deps.get_db),
    request: ExecuteWithModelRequest,
    current_user = Depends(deps.get_current_active_user)
):
    """使用指定模型执行"""
    
    try:
        # 构建执行参数
        exec_kwargs = {}
        if request.temperature is not None:
            exec_kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            exec_kwargs["max_tokens"] = request.max_tokens
        
        # 执行模型调用
        executor = get_model_executor()
        result = await executor.execute_with_specific_model(
            model_id=request.model_id,
            prompt=request.prompt,
            db=db,
            **exec_kwargs
        )
        
        return ExecutionResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"指定模型执行失败: {str(e)}"
        )


@router.get("/test-selection")
async def test_model_selection(
    *,
    db: Session = Depends(deps.get_db),
    requires_thinking: bool = False,
    cost_sensitive: bool = False,
    speed_priority: bool = False,
    current_user = Depends(deps.get_current_active_user)
):
    """测试模型选择逻辑（不执行实际调用）"""
    
    try:
        from app.services.infrastructure.ai.llm.simple_model_selector import get_simple_model_selector
        
        # 构建任务需求
        task_requirement = TaskRequirement(
            requires_thinking=requires_thinking,
            cost_sensitive=cost_sensitive,
            speed_priority=speed_priority
        )
        
        # 获取选择结果
        selector = get_simple_model_selector()
        selection = selector.select_model_for_user(
            user_id=str(current_user.id),
            task_requirement=task_requirement,
            db=db
        )
        
        if not selection:
            return {
                "success": False,
                "message": "未找到可用的模型",
                "user_id": str(current_user.id)
            }
        
        return {
            "success": True,
            "selection": {
                "model_id": selection.model_id,
                "model_name": selection.model_name,
                "model_type": selection.model_type.value,
                "server_id": selection.server_id,
                "server_name": selection.server_name,
                "provider_type": selection.provider_type,
                "reasoning": selection.reasoning,
                "fallback_model_id": selection.fallback_model_id
            },
            "task_requirement": {
                "requires_thinking": task_requirement.requires_thinking,
                "cost_sensitive": task_requirement.cost_sensitive,
                "speed_priority": task_requirement.speed_priority
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试选择失败: {str(e)}"
        )