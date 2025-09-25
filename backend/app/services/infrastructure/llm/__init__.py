"""
React Agent架构的LLM服务基础设施模块

纯数据库驱动的LLM管理，完全基于React Agent系统
与用户LLM偏好和服务器配置完全集成
"""

from typing import Dict, List, Optional, Any

# 核心LLM接口
from .pure_database_manager import (
    get_pure_llm_manager,
    select_model_for_user,
    ask_agent
)

# 模型执行器
from .model_executor import (
    get_model_executor,
    ModelExecutor
)

# 任务需求定义（从simple_model_selector迁移）
from .pure_database_manager import TaskRequirement, ModelSelection

# 步骤选择器
from .step_based_model_selector import (
    create_step_based_model_selector,
    TaskComplexity,
    ProcessingStep,
    StepContext,
    StepBasedModelSelector
)

# 协议适配器
from .protocols import (
    OpenAIAdapter, OpenAIModel, ResponseFormat, OpenAIConfig, create_openai_adapter,
    ProtocolType, ProtocolAdapterFactory
)

# === 主要接口 ===

async def get_llm_manager():
    """获取纯数据库驱动的LLM管理器"""
    return get_pure_llm_manager()


async def select_best_model_for_user(
    user_id: str,
    task_type: str,
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """为用户选择最佳模型"""
    return await select_model_for_user(
        user_id=user_id,
        task_type=task_type,
        complexity=complexity,
        constraints=constraints,
        agent_id=agent_id
    )


async def ask_agent_for_user(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general",
    complexity: str = "medium",
    enable_agent_mode: bool = True,
    **kwargs
) -> str:
    """
    Agent友好的问答接口 - 统一入口
    
    Args:
        user_id: 用户ID
        question: 问题
        agent_type: Agent类型
        context: 上下文
        task_type: 任务类型
        complexity: 复杂度
        enable_agent_mode: 是否启用Agent模式（工具调用、ReAct等）
        **kwargs: 额外参数（enable_tools, enable_react等）
        
    Returns:
        响应文本或Agent响应结果
    """
    
    # 如果启用Agent模式，使用Agent集成管理器
    if enable_agent_mode:
        try:
            from .agent_integrated_manager import ask_agent_enhanced
            
            result = await ask_agent_enhanced(
                user_id=user_id,
                question=question,
                agent_type=agent_type,
                context=context,
                task_type=task_type,
                complexity=complexity,
                enable_tools=kwargs.get("enable_tools", True),
                enable_react=kwargs.get("enable_react", True),
                session_id=kwargs.get("session_id")
            )
            
            # 如果调用者需要完整结果，返回字典；否则返回文本
            if kwargs.get("return_full_result", False):
                return result
            else:
                return result["response"]
                
        except Exception as e:
            # Agent模式失败，回退到基础模式
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Agent模式执行失败，回退到基础模式: {e}")
    
    # 基础模式：使用原始ask_agent
    return await ask_agent(
        user_id=user_id,
        question=question,
        agent_type=agent_type,
        context=context,
        task_type=task_type,
        complexity=complexity
    )


async def get_user_available_models(
    user_id: str,
    model_type: Optional[str] = None,
    provider_name: Optional[str] = None
) -> Dict[str, Any]:
    """获取用户可用的模型列表"""
    manager = get_pure_llm_manager()
    return await manager.get_user_available_models(
        user_id=user_id,
        model_type=model_type,
        provider_name=provider_name
    )


async def get_user_preferences(user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户LLM偏好"""
    manager = get_pure_llm_manager()
    return await manager.get_user_preferences(user_id)


def record_usage_feedback(
    user_id: str,
    model: str,
    provider: str,
    success: bool,
    satisfaction_score: float,
    actual_cost: Optional[float] = None,
    actual_latency: Optional[int] = None,
    agent_id: Optional[str] = None,
    task_type: Optional[str] = None
):
    """记录用户使用反馈"""
    manager = get_pure_llm_manager()
    manager.record_usage_feedback(
        user_id=user_id,
        model=model,
        provider=provider,
        success=success,
        satisfaction_score=satisfaction_score,
        actual_cost=actual_cost,
        actual_latency=actual_latency,
        agent_id=agent_id,
        task_type=task_type
    )


async def health_check() -> Dict[str, Any]:
    """LLM服务健康检查"""
    try:
        manager = get_pure_llm_manager()
        return await manager.health_check()
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "error": str(e),
            "manager_type": "pure_database_driven"
        }


# === 服务信息 ===

def get_service_info() -> Dict[str, Any]:
    """获取LLM服务信息"""
    manager = get_pure_llm_manager()
    return manager.get_service_info()


__all__ = [
    # 核心接口
    "get_llm_manager",
    "select_best_model_for_user", 
    "ask_agent_for_user",
    "get_user_available_models",
    "get_user_preferences",
    "record_usage_feedback",
    "health_check",
    "get_service_info",
    
    # Agent系统接口
    "get_model_executor",
    "create_step_based_model_selector",
    "TaskRequirement",
    "TaskComplexity",
    "ProcessingStep",
    "StepContext",
    "ask_agent",
    
    # 类定义
    "ModelExecutor",
    "StepBasedModelSelector",
    "ModelSelection",
    
    # 协议适配器
    "OpenAIAdapter",
    "OpenAIModel",
    "ResponseFormat", 
    "OpenAIConfig",
    "create_openai_adapter",
    "ProtocolType",
    "ProtocolAdapterFactory"
]