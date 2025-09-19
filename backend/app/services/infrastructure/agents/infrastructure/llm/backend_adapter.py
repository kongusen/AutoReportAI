"""
Backend LLM服务适配器
连接Laboratory框架Agent系统与现有的LLM基础设施
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

from .base import BaseLLMProvider, LLMResponse, LLMStreamChunk

# 导入现有的LLM服务
try:
    from app.services.infrastructure.llm import (
        ask_agent_for_user,
        select_best_model_for_user,
        get_user_available_models,
        get_model_executor,
        ModelExecutor
    )
    BACKEND_LLM_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Backend LLM service not available: {e}")
    BACKEND_LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class BackendLLMAdapter(BaseLLMProvider):
    """
    Backend LLM服务适配器
    
    将Laboratory框架的LLM接口适配到现有的Backend LLM服务
    让Agent可以通过统一接口使用现有的LLM基础设施
    """
    
    def __init__(self, default_user_id: str = "agent_system"):
        """
        初始化适配器
        
        Args:
            default_user_id: 默认用户ID，用于Agent系统调用
        """
        super().__init__()
        self.default_user_id = default_user_id
        self.model_executor: Optional[ModelExecutor] = None
        self._is_available = BACKEND_LLM_AVAILABLE
        
        if self._is_available:
            try:
                # 获取模型执行器
                self.model_executor = get_model_executor()
                logger.info("BackendLLMAdapter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize model executor: {e}")
                self._is_available = False
        else:
            logger.warning("Backend LLM service not available, using fallback mode")
    
    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: str = "placeholder_agent",
        task_type: str = "general",
        complexity: str = "medium",
        **kwargs
    ) -> LLMResponse:
        """
        生成响应
        
        Args:
            prompt: 输入提示
            model: 指定模型（可选）
            user_id: 用户ID（可选，默认使用default_user_id）
            agent_type: Agent类型
            task_type: 任务类型
            complexity: 复杂度
        """
        if not self._is_available:
            return self._fallback_response(prompt)
        
        try:
            actual_user_id = user_id or self.default_user_id
            
            # 使用现有的ask_agent_for_user接口
            response_text = await ask_agent_for_user(
                user_id=actual_user_id,
                question=prompt,
                agent_type=agent_type,
                context=kwargs.get('context'),
                task_type=task_type,
                complexity=complexity
            )
            
            return LLMResponse(
                content=response_text,
                model=model or "backend_selected",
                usage={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response_text.split()),
                    "total_tokens": len(prompt.split()) + len(response_text.split())
                },
                metadata={
                    "user_id": actual_user_id,
                    "agent_type": agent_type,
                    "task_type": task_type,
                    "complexity": complexity,
                    "backend_adapter": True
                }
            )
            
        except Exception as e:
            logger.error(f"Backend LLM call failed: {e}")
            return self._fallback_response(prompt, error=str(e))
    
    async def stream_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: str = "placeholder_agent",
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        流式生成响应
        
        注意：当前backend LLM服务可能不支持流式，这里模拟流式输出
        """
        try:
            # 先获取完整响应
            response = await self.generate_response(
                prompt=prompt,
                model=model,
                user_id=user_id,
                agent_type=agent_type,
                **kwargs
            )
            
            # 模拟流式输出
            content = response.content
            chunk_size = 50  # 每个chunk的大小
            
            for i in range(0, len(content), chunk_size):
                chunk_text = content[i:i + chunk_size]
                
                yield LLMStreamChunk(
                    content=chunk_text,
                    delta=chunk_text,
                    model=response.model,
                    is_final=(i + chunk_size >= len(content)),
                    metadata=response.metadata
                )
                
                # 模拟流式延迟
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Stream response failed: {e}")
            yield LLMStreamChunk(
                content=f"Error: {e}",
                delta=f"Error: {e}",
                model=model or "error",
                is_final=True,
                metadata={"error": True}
            )
    
    async def select_best_model(
        self,
        task_type: str,
        complexity: str = "medium",
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        选择最佳模型
        
        使用backend的模型选择逻辑
        """
        if not self._is_available:
            return {
                "model": "fallback",
                "provider": "mock",
                "reason": "Backend LLM service not available"
            }
        
        try:
            actual_user_id = user_id or self.default_user_id
            
            selection = await select_best_model_for_user(
                user_id=actual_user_id,
                task_type=task_type,
                complexity=complexity,
                constraints=constraints,
                agent_id=agent_id
            )
            
            return selection
            
        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            return {
                "model": "fallback",
                "provider": "error",
                "reason": f"Selection failed: {e}"
            }
    
    async def get_available_models(
        self,
        user_id: Optional[str] = None,
        model_type: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        """
        if not self._is_available:
            return [{"model": "fallback", "provider": "mock", "available": True}]
        
        try:
            actual_user_id = user_id or self.default_user_id
            
            models_info = await get_user_available_models(
                user_id=actual_user_id,
                model_type=model_type,
                provider_name=provider_name
            )
            
            # 转换为统一格式
            models_list = []
            if isinstance(models_info, dict) and "models" in models_info:
                for model_info in models_info["models"]:
                    models_list.append({
                        "model": model_info.get("model", "unknown"),
                        "provider": model_info.get("provider", "unknown"),
                        "available": model_info.get("available", True),
                        "capabilities": model_info.get("capabilities", []),
                        "cost": model_info.get("cost_info", {})
                    })
            
            return models_list
            
        except Exception as e:
            logger.error(f"Get available models failed: {e}")
            return [{"model": "error", "provider": "error", "available": False, "error": str(e)}]
    
    def _fallback_response(self, prompt: str, error: Optional[str] = None) -> LLMResponse:
        """回退响应，当backend服务不可用时使用"""
        
        fallback_content = self._generate_fallback_content(prompt)
        
        if error:
            fallback_content = f"[Fallback Mode - Backend Error: {error}]\n\n{fallback_content}"
        else:
            fallback_content = f"[Fallback Mode - Backend Unavailable]\n\n{fallback_content}"
        
        return LLMResponse(
            content=fallback_content,
            model="fallback",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            metadata={
                "fallback": True,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _generate_fallback_content(self, prompt: str) -> str:
        """生成回退内容"""
        prompt_lower = prompt.lower()
        
        if "sql" in prompt_lower or "数据库" in prompt_lower:
            return """
```sql
-- 基于提示生成的基础SQL查询
SELECT 
    id,
    name,
    value,
    created_at
FROM data_table 
WHERE active = true
ORDER BY created_at DESC
LIMIT 100;
```

这是一个基础的SQL查询模板。在正常情况下，backend LLM服务会根据具体需求生成更精确的查询。
"""
        
        elif "分析" in prompt_lower or "analysis" in prompt_lower:
            return """
基于当前可用信息的分析：

## 主要发现
- 数据显示了明显的模式
- 需要进一步的数据收集来确认趋势
- 建议采用多维度分析方法

## 建议
1. 收集更多历史数据
2. 进行对比分析
3. 监控关键指标变化

注：这是回退模式下的简化分析。完整分析需要backend LLM服务支持。
"""
        
        else:
            return f"""
收到您的请求：{prompt[:100]}{'...' if len(prompt) > 100 else ''}

这是fallback模式下的响应。正常情况下，系统会通过backend LLM服务提供更详细和准确的回答。

建议：
1. 检查backend LLM服务状态
2. 确认网络连接
3. 联系系统管理员
"""

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self._is_available:
            return {
                "status": "unhealthy",
                "backend_available": False,
                "reason": "Backend LLM service not available"
            }
        
        try:
            # 使用backend的健康检查
            from app.services.infrastructure.llm import health_check
            backend_health = await health_check()
            
            return {
                "status": "healthy" if backend_health.get("healthy", False) else "degraded",
                "backend_available": True,
                "backend_health": backend_health,
                "adapter_info": {
                    "default_user_id": self.default_user_id,
                    "model_executor_available": self.model_executor is not None
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend_available": False,
                "error": str(e)
            }

    # Implement BaseLLMProvider expected streaming interface
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """将 messages 适配为 prompt，并复用 stream_response 回退逻辑"""
        # 简单将消息拼接为 prompt
        parts = []
        for m in messages or []:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"[{role}] {content}")
        prompt = "\n\n".join(parts)

        async for chunk in self.stream_response(
            prompt=prompt,
            model=kwargs.get("model"),
            user_id=kwargs.get("user_id"),
            agent_type=kwargs.get("agent_type", "placeholder_agent"),
        ):
            # 保障 chunk_type 存在
            if not getattr(chunk, "chunk_type", None):
                chunk.chunk_type = "text"
            yield chunk


# 工厂函数和全局实例管理
_global_adapter: Optional[BackendLLMAdapter] = None

def get_backend_llm_adapter(user_id: str = "agent_system") -> BackendLLMAdapter:
    """获取Backend LLM适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = BackendLLMAdapter(default_user_id=user_id)
    return _global_adapter

def create_backend_llm_adapter(user_id: str = "agent_system") -> BackendLLMAdapter:
    """创建新的Backend LLM适配器实例"""
    return BackendLLMAdapter(default_user_id=user_id)

# Agent友好的便捷接口
async def agent_ask(
    prompt: str,
    agent_type: str = "placeholder_agent",
    task_type: str = "general",
    complexity: str = "medium",
    user_id: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """Agent友好的问答接口"""
    adapter = get_backend_llm_adapter()
    response = await adapter.generate_response(
        prompt=prompt,
        model=model,
        user_id=user_id,
        agent_type=agent_type,
        task_type=task_type,
        complexity=complexity
    )
    return response.content

async def agent_select_model(
    task_type: str,
    complexity: str = "medium",
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """Agent友好的模型选择接口"""
    adapter = get_backend_llm_adapter()
    return await adapter.select_best_model(
        task_type=task_type,
        complexity=complexity,
        user_id=user_id,
        agent_id=agent_id
    )
