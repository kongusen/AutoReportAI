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

# 简化选择器
from .simple_model_selector import (
    get_simple_model_selector,
    TaskRequirement,
    ModelSelection,
    SimpleModelSelector
)

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
    complexity: str = "medium"
) -> str:
    """Agent友好的问答接口 - 需要用户ID"""
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
    "get_simple_model_selector",
    "create_step_based_model_selector",
    "TaskRequirement",
    "TaskComplexity",
    "ProcessingStep",
    "StepContext",
    "ask_agent",
    
    # 类定义
    "ModelExecutor",
    "SimpleModelSelector",
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