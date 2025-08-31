"""
LLM适配器
将现有的LLM管理器适配为LlamaIndex LLM接口
"""

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from pydantic import BaseModel

from llama_index.core.llms.llm import LLM
from llama_index.core.llms.callbacks import CallbackManager
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata
)

from ...llm.client import (
    LLMServerClient, 
    get_llm_client,
    LLMRequest,
    LLMMessage as LLMRequestMessage
)
from .llm_router import (
    get_abstract_llm_router,
    TaskComplexity,
    TaskContext,
    AbstractModelType
)

logger = logging.getLogger(__name__)


class LLMClientAdapter(LLM):
    """
    智能LLM客户端适配器类
    将AutoReportAI的LLMServerClient适配为LlamaIndex LLM接口
    支持基于任务类型和复杂度的智能模型路由
    """
    
    def __init__(
        self,
        agent_type: str = "general",
        user_id: str = "system",
        fixed_model: Optional[str] = None,
        callback_manager: Optional[CallbackManager] = None,
        **kwargs: Any
    ):
        super().__init__(callback_manager=callback_manager, **kwargs)
        
        self.agent_type = agent_type
        self.user_id = user_id
        self.fixed_model = fixed_model  # 如果设置，则不使用路由
        self.router = get_llm_router()
        
        # 获取全局LLM客户端实例
        self.llm_client = get_llm_client()
        
        # 当前使用的模型配置
        self.current_model_config: Optional[Dict[str, Any]] = None
        
        # 如果指定了固定模型，创建默认配置
        if fixed_model:
            self.current_model_config = {
                "provider": "openai",  # 默认提供商
                "model_name": fixed_model
            }
            model_name = fixed_model
            context_window = 8192
        else:
            # 使用默认配置
            self.current_model_config = {
                "provider": "openai",
                "model_name": "gpt-4o-mini"
            }
            model_name = "gpt-4o-mini"
            context_window = 8192
        
        # 设置元数据
        self._metadata = LLMMetadata(
            model_name=model_name,
            context_window=context_window,
            num_output=4096,
            is_chat_model=True,
            is_function_calling_model=True
        )
    
    @property
    def metadata(self) -> LLMMetadata:
        """返回LLM元数据"""
        return self._metadata
    
    @property
    def model(self) -> str:
        """返回模型名称"""
        return self.model_name
    
    def _prepare_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """准备消息格式"""
        prepared_messages = []
        for msg in messages:
            prepared_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return prepared_messages
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """同步聊天接口"""
        # 由于我们的LLMClient是异步的，这里抛出未实现错误
        # 在实际使用中，应该使用achat方法
        raise NotImplementedError(
            "同步聊天接口未实现，请使用异步接口 achat"
        )
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """同步补全接口"""
        raise NotImplementedError(
            "同步补全接口未实现，请使用异步接口 acomplete"
        )
    
    def stream_chat(
        self, messages: List[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """同步流式聊天接口"""
        raise NotImplementedError(
            "同步流式接口未实现，请使用异步接口 astream_chat"
        )
    
    def stream_complete(
        self, prompt: str, **kwargs: Any
    ) -> CompletionResponseGen:
        """同步流式补全接口"""
        raise NotImplementedError(
            "同步流式接口未实现，请使用异步接口 astream_complete"
        )
    
    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """异步聊天接口 - 支持智能路由"""
        import time
        start_time = time.time()
        
        try:
            # 获取任务上下文信息
            task_context = self._create_task_context(messages, **kwargs)
            
            # 如果没有固定模型，使用路由选择最佳模型
            if not self.fixed_model:
                self.current_model_config = self.router.route_llm(task_context)
                logger.info(f"路由选择模型: {self.current_model_config.provider}/{self.current_model_config.model_name}")
            
            # 准备消息格式 - 转换为LLMServerClient需要的格式
            llm_messages = [
                LLMRequestMessage(role=msg.role.value, content=msg.content) 
                for msg in messages
            ]
            
            # 创建LLM请求，使用路由选择的模型
            request = LLMRequest(
                messages=llm_messages,
                model=self.current_model_config.model_name,
                user_id=self.user_id,
                max_tokens=self.current_model_config.max_tokens,
                temperature=self.current_model_config.temperature,
                **kwargs
            )
            
            # 调用LLM客户端
            response = await self.llm_client.chat_completion_with_retry(request)
            
            # 记录性能统计
            response_time = time.time() - start_time
            self.router.record_performance(
                model=self.current_model_config,
                task_context=task_context,
                success=True,
                response_time=response_time,
                token_usage=response.usage
            )
            
            # 转换为ChatResponse格式
            return ChatResponse(
                message=ChatMessage(role="assistant", content=response.content),
                raw={
                    "model": response.model,
                    "provider": response.provider,
                    "usage": response.usage,
                    "response_time": response.response_time,
                    "timestamp": response.timestamp.isoformat(),
                    "routed_model": f"{self.current_model_config.provider}/{self.current_model_config.model_name}",
                    "task_context": task_context.task_type.value
                }
            )
            
        except Exception as e:
            # 记录失败统计
            response_time = time.time() - start_time
            if hasattr(self, 'current_model_config') and self.current_model_config:
                task_context = self._create_task_context(messages, **kwargs)
                self.router.record_performance(
                    model=self.current_model_config,
                    task_context=task_context,
                    success=False,
                    response_time=response_time
                )
            
            logger.error(f"LLM聊天调用失败: {e}")
            # 返回错误响应
            return ChatResponse(
                message=ChatMessage(
                    role="assistant", 
                    content=f"抱歉，我遇到了技术问题：{str(e)}"
                ),
                raw={"error": str(e)}
            )
    
    def _create_task_context(self, messages: List[ChatMessage], **kwargs) -> TaskContext:
        """根据消息和参数创建任务上下文"""
        # 合并所有消息内容用于分析
        combined_content = " ".join([msg.content for msg in messages])
        
        # 估算token数量（粗略估算）
        estimated_tokens = len(combined_content.split()) * 1.3
        
        # 根据Agent类型确定任务类型（简化版）
        agent_task_mapping = {
            "general": "default",
            "placeholder_expert": "placeholder_analysis",
            "chart_specialist": "chart_generation", 
            "data_analyst": "data_analysis"
        }
        
        task_type = agent_task_mapping.get(self.agent_type, "default")
        
        # 根据内容长度和关键词判断复杂度
        complexity = self._estimate_task_complexity(combined_content)
        
        # 检查是否需要函数调用
        requires_function_calling = (
            self.agent_type != "general" or
            "工具" in combined_content or
            "函数" in combined_content or
            "调用" in combined_content
        )
        
        # 检查是否需要长上下文
        requires_long_context = len(combined_content) > 8000
        
        return TaskContext(
            task_type=task_type,
            complexity=complexity,
            estimated_tokens=int(estimated_tokens),
            requires_function_calling=requires_function_calling,
            requires_long_context=requires_long_context,
            user_id=self.user_id,
            priority=kwargs.get('priority', 5),
            budget_constraint=kwargs.get('budget_constraint'),
            time_constraint=kwargs.get('time_constraint')
        )
    
    def _estimate_task_complexity(self, content: str) -> TaskComplexity:
        """估算任务复杂度"""
        # 基于内容长度的基础判断
        if len(content) > 2000:
            base_complexity = TaskComplexity.HIGH
        elif len(content) > 800:
            base_complexity = TaskComplexity.MEDIUM
        else:
            base_complexity = TaskComplexity.SIMPLE
        
        # 基于关键词的复杂度调整
        high_complexity_keywords = [
            "推理", "分析", "复杂", "详细", "深入", "综合", "多步", 
            "逻辑", "因果", "推导", "解释", "论证"
        ]
        
        medium_complexity_keywords = [
            "比较", "总结", "归纳", "整理", "分类", "计算", "查询"
        ]
        
        high_keyword_count = sum(1 for keyword in high_complexity_keywords if keyword in content)
        medium_keyword_count = sum(1 for keyword in medium_complexity_keywords if keyword in content)
        
        # 根据关键词调整复杂度
        if high_keyword_count >= 2:
            return TaskComplexity.VERY_HIGH
        elif high_keyword_count >= 1 or (base_complexity == TaskComplexity.HIGH):
            return TaskComplexity.HIGH
        elif medium_keyword_count >= 1 or (base_complexity == TaskComplexity.MEDIUM):
            return TaskComplexity.MEDIUM
        else:
            return base_complexity
    
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """异步补全接口"""
        try:
            # 将prompt转换为messages格式
            messages = [ChatMessage(role="user", content=prompt)]
            
            chat_response = await self.achat(messages, **kwargs)
            
            return CompletionResponse(
                text=chat_response.message.content,
                raw=chat_response.raw
            )
            
        except Exception as e:
            logger.error(f"LLM补全调用失败: {e}")
            return CompletionResponse(
                text=f"抱歉，我遇到了技术问题：{str(e)}",
                raw={"error": str(e)}
            )
    
    async def astream_chat(
        self, messages: List[ChatMessage], **kwargs: Any
    ) -> AsyncGenerator[ChatResponse, None]:
        """异步流式聊天接口"""
        # 目前先实现非流式版本
        response = await self.achat(messages, **kwargs)
        yield response
    
    async def astream_complete(
        self, prompt: str, **kwargs: Any
    ) -> AsyncGenerator[CompletionResponse, None]:
        """异步流式补全接口"""
        # 目前先实现非流式版本
        response = await self.acomplete(prompt, **kwargs)
        yield response
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 使用简单的测试消息检查LLM状态
            test_messages = [ChatMessage(role="user", content="Hello")]
            response = await self.achat(test_messages)
            
            return {
                "status": "healthy",
                "model": self.model_name,
                "user_id": self.user_id,
                "response_received": bool(response.message.content)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "model": self.model_name,
                "user_id": self.user_id,
                "error": str(e)
            }


async def create_llm_adapter(
    agent_type: str = "general",
    user_id: str = "system", 
    fixed_model: Optional[str] = None,
    **kwargs: Any
) -> LLMClientAdapter:
    """
    创建智能LLM客户端适配器实例
    
    Args:
        agent_type: 代理类型，用于路由模型选择
        user_id: 用户ID
        fixed_model: 固定模型名称，如果指定则不使用路由
        **kwargs: 其他参数
        
    Returns:
        配置好的LLM客户端适配器实例
    """
    try:
        adapter = LLMClientAdapter(
            agent_type=agent_type,
            user_id=user_id,
            fixed_model=fixed_model,
            **kwargs
        )
        
        if fixed_model:
            logger.info(f"创建固定模型LLM适配器 - 代理: {agent_type}, 模型: {fixed_model}, 用户: {user_id}")
        else:
            logger.info(f"创建智能路由LLM适配器 - 代理: {agent_type}, 用户: {user_id}")
        
        return adapter
        
    except Exception as e:
        logger.error(f"创建LLM适配器失败: {e}")
        raise


async def create_agent_llm(agent_type: str, user_id: str = "system") -> LLMClientAdapter:
    """
    为特定代理类型创建智能LLM适配器
    
    Args:
        agent_type: 代理类型 (general, placeholder_expert, chart_specialist, data_analyst)
        user_id: 用户ID
        
    Returns:
        配置好的智能路由LLM适配器
    """
    return await create_llm_adapter(
        agent_type=agent_type,
        user_id=user_id
    )


# 便捷函数：创建具有固定模型的适配器
async def create_fixed_model_adapter(
    model_name: str,
    agent_type: str = "general", 
    user_id: str = "system"
) -> LLMClientAdapter:
    """
    创建使用固定模型的LLM适配器
    
    Args:
        model_name: 固定的模型名称
        agent_type: 代理类型
        user_id: 用户ID
        
    Returns:
        使用固定模型的适配器
    """
    return await create_llm_adapter(
        agent_type=agent_type,
        user_id=user_id,
        fixed_model=model_name
    )


# 路由统计和监控函数
def get_llm_routing_stats() -> Dict[str, Any]:
    """获取LLM路由统计信息"""
    router = get_llm_router()
    return router.get_routing_stats()


def get_model_performance_report() -> Dict[str, Any]:
    """获取模型性能报告"""
    router = get_llm_router()
    stats = router.get_routing_stats()
    
    performance_data = stats.get("performance_stats", {})
    
    # 计算总体统计
    total_requests = 0
    successful_requests = 0
    total_response_time = 0.0
    
    model_summary = {}
    
    for model_key, task_stats in performance_data.items():
        model_total = 0
        model_success = 0
        model_time = 0.0
        
        for _, metrics in task_stats.items():
            model_total += metrics.get("total_requests", 0)
            model_success += metrics.get("successful_requests", 0)
            model_time += metrics.get("total_response_time", 0.0)
        
        if model_total > 0:
            model_summary[model_key] = {
                "total_requests": model_total,
                "success_rate": model_success / model_total,
                "avg_response_time": model_time / model_total
            }
        
        total_requests += model_total
        successful_requests += model_success
        total_response_time += model_time
    
    return {
        "overall_stats": {
            "total_requests": total_requests,
            "overall_success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "overall_avg_response_time": total_response_time / total_requests if total_requests > 0 else 0
        },
        "model_performance": model_summary,
        "raw_performance_data": performance_data
    }