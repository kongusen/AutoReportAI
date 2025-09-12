"""
模型执行API端点
提供基于用户配置的实际模型调用接口
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps

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
    current_user = Depends(deps.get_current_active_user),
    execute_agent_task = Depends(deps.get_agents_executor)
):
    """基于任务需求自动选择模型并执行 - 使用agents系统"""
    
    try:
        # 使用新的agents系统
        from app.api.utils.agent_context_helpers import create_task_execution_context
        
        # 确定任务类型
        task_type = "general"
        if request.requires_thinking:
            task_type = "complex_reasoning"
        elif request.speed_priority:
            task_type = "quick_response"
        elif request.cost_sensitive:
            task_type = "cost_efficient"
        
        # 准备任务数据
        task_data = {
            "prompt": request.prompt,
            "requires_thinking": request.requires_thinking,
            "cost_sensitive": request.cost_sensitive,
            "speed_priority": request.speed_priority,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "user_id": str(current_user.id)
        }
        
        execution_options = {
            "task_type": task_type,
            "timeout_seconds": 300,
            "enable_streaming": request.speed_priority,
            "cost_optimization": request.cost_sensitive
        }
        
        # 创建任务执行上下文
        context = create_task_execution_context(
            task_name="模型执行",
            task_description=f"执行{task_type}任务",
            task_data=task_data,
            execution_options=execution_options
        )
        
        # 执行agents任务
        result = await execute_agent_task(
            task_name="model_execution",
            task_description=f"执行{task_type}模型调用",
            context_data=context,
            additional_data={
                "user_id": str(current_user.id),
                "prompt": request.prompt,
                "execution_params": {
                    "requires_thinking": request.requires_thinking,
                    "cost_sensitive": request.cost_sensitive,
                    "speed_priority": request.speed_priority,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                }
            }
        )
        
        return ExecutionResponse(
            success=result.get('success', True),
            result=result.get('response', str(result)),
            selected_model=result.get('selected_model'),
            tokens_used=result.get('tokens_used'),
            response_time_ms=result.get('response_time_ms'),
            used_fallback=result.get('used_fallback', False)
        )
        
    except Exception as e:
        return ExecutionResponse(
            success=False,
            error=f"模型执行失败: {str(e)}"
        )


@router.post("/execute-with-model", response_model=ExecutionResponse)
async def execute_with_specific_model(
    *,
    db: Session = Depends(deps.get_db),
    request: ExecuteWithModelRequest,
    current_user = Depends(deps.get_current_active_user),
    execute_agent_task = Depends(deps.get_agents_executor)
):
    """使用指定模型执行 - 使用agents系统"""
    
    try:
        # 使用新的agents系统
        from app.api.utils.agent_context_helpers import create_task_execution_context
        
        # 准备任务数据
        task_data = {
            "model_id": request.model_id,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "user_id": str(current_user.id)
        }
        
        execution_options = {
            "specific_model": request.model_id,
            "timeout_seconds": 300
        }
        
        # 创建任务执行上下文
        context = create_task_execution_context(
            task_name="指定模型执行",
            task_description=f"使用模型ID {request.model_id} 执行任务",
            task_data=task_data,
            execution_options=execution_options
        )
        
        # 执行agents任务
        result = await execute_agent_task(
            task_name="specific_model_execution",
            task_description=f"使用指定模型 {request.model_id} 执行任务",
            context_data=context,
            additional_data={
                "user_id": str(current_user.id),
                "model_id": request.model_id,
                "prompt": request.prompt,
                "execution_params": {
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                }
            }
        )
        
        return ExecutionResponse(
            success=result.get('success', True),
            result=result.get('response', str(result)),
            selected_model={"id": request.model_id},
            tokens_used=result.get('tokens_used'),
            response_time_ms=result.get('response_time_ms'),
            used_fallback=result.get('used_fallback', False)
        )
        
    except Exception as e:
        return ExecutionResponse(
            success=False,
            error=f"指定模型执行失败: {str(e)}"
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
        # 使用agents系统进行模型选择测试
        # No actual context creation needed for testing
        
        # 确定任务类型
        task_type = "general"
        if requires_thinking:
            task_type = "complex_reasoning"
        elif speed_priority:
            task_type = "quick_response"
        elif cost_sensitive:
            task_type = "cost_efficient"
        
        # 模拟选择结果（实际上agents系统内部处理模型选择）
        selection = {
            "task_type": task_type,
            "requires_thinking": requires_thinking,
            "cost_sensitive": cost_sensitive,
            "speed_priority": speed_priority,
            "recommended_approach": f"agents系统将自动为{task_type}任务选择最合适的处理方式"
        }
        
        return {
            "success": True,
            "selection": selection,
            "architecture": "agents_v2",
            "message": f"agents系统将智能选择最适合{task_type}任务的处理方式",
            "task_requirement": {
                "requires_thinking": requires_thinking,
                "cost_sensitive": cost_sensitive,
                "speed_priority": speed_priority,
                "task_type": task_type
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试选择失败: {str(e)}"
        )