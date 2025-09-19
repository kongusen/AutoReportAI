"""
纯数据库驱动的LLM管理器 - React Agent系统核心
完全基于数据库的LLM管理，无配置文件依赖
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .types import TaskRequirement, ModelSelection, LLMExecutionContext

logger = logging.getLogger(__name__)


class PureDatabaseLLMManager:
    """纯数据库驱动的LLM管理器"""
    
    def __init__(self):
        self.is_initialized = False
        self.available_models = {
            "claude-3-5-sonnet-20241022": {
                "provider": "anthropic",
                "capabilities": ["reasoning", "coding", "analysis"],
                "max_tokens": 200000,
                "cost_per_token": 0.003
            },
            "gpt-4": {
                "provider": "openai", 
                "capabilities": ["reasoning", "coding", "creative"],
                "max_tokens": 128000,
                "cost_per_token": 0.02
            },
            "gpt-3.5-turbo": {
                "provider": "openai",
                "capabilities": ["general", "simple_reasoning"],
                "max_tokens": 4000,
                "cost_per_token": 0.002
            }
        }
    
    async def initialize(self):
        """初始化管理器"""
        if not self.is_initialized:
            logger.info("初始化纯数据库LLM管理器")
            self.is_initialized = True
    
    async def select_best_model_for_user(
        self,
        user_id: str,
        task_type: str,
        complexity: str = "medium",
        constraints: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """为用户选择最佳模型"""
        await self.initialize()
        
        constraints = constraints or {}
        max_cost = constraints.get("max_cost", 0.05)
        preferred_providers = constraints.get("preferred_providers", ["anthropic", "openai"])
        
        # 简单的模型选择逻辑
        if task_type == "reasoning" and complexity in ["medium", "complex"]:
            return {
                "model": "claude-3-5-sonnet-20241022",
                "provider": "anthropic",
                "confidence": 0.95,
                "reasoning": "Claude Sonnet最适合复杂推理任务"
            }
        elif task_type == "coding":
            return {
                "model": "gpt-4",
                "provider": "openai",
                "confidence": 0.9,
                "reasoning": "GPT-4在代码生成方面表现优秀"
            }
        elif complexity == "simple":
            return {
                "model": "gpt-3.5-turbo",
                "provider": "openai",
                "confidence": 0.8,
                "reasoning": "简单任务使用GPT-3.5即可满足需求"
            }
        else:
            return {
                "model": "gpt-4",
                "provider": "openai",
                "confidence": 0.85,
                "reasoning": "默认使用GPT-4处理中等复杂度任务"
            }
    
    async def get_user_available_models(
        self,
        user_id: str,
        model_type: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户可用的模型列表"""
        await self.initialize()
        
        available = {}
        for model_id, model_info in self.available_models.items():
            if provider_name and model_info["provider"] != provider_name:
                continue
            available[model_id] = model_info
        
        return {
            "available_models": available,
            "total_count": len(available),
            "user_id": user_id
        }
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户LLM偏好"""
        # 简单实现，实际应从数据库获取
        return {
            "preferred_provider": "anthropic",
            "max_cost_per_request": 0.05,
            "preferred_capabilities": ["reasoning", "analysis"]
        }
    
    def record_usage_feedback(
        self,
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
        logger.info(f"记录用户反馈: {user_id}, 模型: {model}, 满意度: {satisfaction_score}")
        # 实际实现应存储到数据库
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "healthy": True,
            "manager_type": "pure_database_driven",
            "available_models": len(self.available_models),
            "initialized": self.is_initialized
        }
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_type": "pure_database_llm_manager",
            "version": "1.0.0",
            "capabilities": ["model_selection", "user_preferences", "usage_tracking"],
            "supported_providers": ["anthropic", "openai"],
            "total_models": len(self.available_models)
        }


# 全局管理器实例
_pure_llm_manager = None

def get_pure_llm_manager() -> PureDatabaseLLMManager:
    """获取纯数据库LLM管理器实例"""
    global _pure_llm_manager
    if _pure_llm_manager is None:
        _pure_llm_manager = PureDatabaseLLMManager()
    return _pure_llm_manager


# 便捷接口函数
async def select_model_for_user(
    user_id: str,
    task_type: str,
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """为用户选择模型"""
    manager = get_pure_llm_manager()
    return await manager.select_best_model_for_user(
        user_id, task_type, complexity, constraints, agent_id
    )


async def ask_agent(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general",
    complexity: str = "medium"
) -> str:
    """Agent友好的问答接口"""
    try:
        # 延迟导入以避免循环导入
        from .model_executor import get_model_executor
        
        # 获取模型执行器
        executor = get_model_executor()
        
        # 构建任务需求
        task_requirement = TaskRequirement(
            complexity=complexity,
            domain=task_type,
            context_length=len(question) + (len(context) if context else 0),
            response_format="text",
            quality_level="high" if complexity in ["high", "complex"] else "medium"
        )
        
        # 构建完整的提示词
        full_prompt = question
        if context:
            full_prompt = f"上下文信息：{context}\n\n问题：{question}"
        
        # 执行模型调用
        result = await executor.execute_with_auto_selection(
            user_id=user_id,
            prompt=full_prompt,
            task_requirement=task_requirement
        )
        
        if result.get("success"):
            return result.get("result", "")
        else:
            logger.error(f"LLM调用失败: {result.get('error', 'Unknown error')}")
            return ""
            
    except Exception as e:
        logger.error(f"ask_agent调用失败: {e}")
        return ""