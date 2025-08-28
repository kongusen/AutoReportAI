"""
OpenAI提供商实现

支持OpenAI官方API和兼容的API端点
"""

import logging
import time
from typing import Any, Dict, List, Union

import openai
from openai import AsyncOpenAI

from .base import BaseLLMProvider
from ..models import LLMRequest, LLMResponse, ProviderConfig, ProviderType, UsageInfo

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI提供商实现"""
    
    def __init__(self, name: str, config: ProviderConfig):
        super().__init__(name, config)
        
        self.client: AsyncOpenAI = None
        
        # OpenAI支持的能力
        self.supports_chat = True
        self.supports_embeddings = True
        self.supports_functions = True
        self.supports_streaming = True
        
        # 默认模型列表（会在初始化时更新）
        self.available_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini"
        ]
        
        # 成本信息（每1K tokens的USD价格）
        self.cost_info = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006}
        }
    
    async def _initialize(self):
        """初始化OpenAI客户端"""
        # 处理API基础URL
        base_url = None
        if self.config.api_base:
            base_url = self._normalize_api_base(self.config.api_base)
        
        # 创建异步客户端
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=base_url,
            organization=self.config.organization,
            timeout=self.config.timeout
        )
        
        # 尝试获取实际可用的模型列表
        try:
            models = await self.client.models.list()
            self.available_models = [model.id for model in models.data]
            logger.info(f"从OpenAI获取到 {len(self.available_models)} 个可用模型")
        except Exception as e:
            logger.warning(f"无法获取OpenAI模型列表，使用默认列表: {e}")
    
    def _normalize_api_base(self, api_base: str) -> str:
        """标准化API基础URL"""
        # 移除末尾的斜杠
        api_base = api_base.rstrip('/')
        
        # 如果包含完整的chat/completions路径，提取base URL
        if '/chat/completions' in api_base:
            api_base = api_base.split('/chat/completions')[0]
        
        # 确保以/v1结尾（如果不是以/v1结尾的话）
        if not api_base.endswith('/v1'):
            api_base += '/v1'
        
        return api_base
    
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """OpenAI聊天完成"""
        self._validate_request(request)
        
        if not self.client:
            raise RuntimeError(f"提供商 {self.name} 未初始化")
        
        start_time = time.time()
        
        try:
            # 准备消息格式
            messages = self._prepare_messages(request.messages)
            
            # 确定使用的模型
            model = request.model or self.config.default_model or "gpt-3.5-turbo"
            
            # 准备API调用参数
            api_params = {
                "model": model,
                "messages": messages,
                "stream": request.stream
            }
            
            # 添加可选参数
            if request.max_tokens:
                api_params["max_tokens"] = request.max_tokens
            if request.temperature is not None:
                api_params["temperature"] = request.temperature
            if request.top_p is not None:
                api_params["top_p"] = request.top_p
            if request.frequency_penalty is not None:
                api_params["frequency_penalty"] = request.frequency_penalty
            if request.presence_penalty is not None:
                api_params["presence_penalty"] = request.presence_penalty
            if request.stop:
                api_params["stop"] = request.stop
            
            # 处理响应格式
            if request.response_format and hasattr(request.response_format, 'value'):
                if request.response_format.value == "json_object":
                    api_params["response_format"] = {"type": "json_object"}
            
            # 处理函数调用
            if request.functions:
                api_params["functions"] = request.functions
            if request.function_call:
                api_params["function_call"] = request.function_call
            if request.tools:
                api_params["tools"] = request.tools
            if request.tool_choice:
                api_params["tool_choice"] = request.tool_choice
            
            # 调用OpenAI API
            response = await self.client.chat.completions.create(**api_params)
            
            response_time = time.time() - start_time
            
            # 提取响应内容
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            
            # 创建使用信息
            usage = self._create_usage_info(
                response.usage.prompt_tokens if response.usage else 0,
                response.usage.completion_tokens if response.usage else 0
            )
            
            # 估算成本
            cost_estimate = self._estimate_cost(model, usage)
            
            # 记录统计
            self._record_request(
                success=True,
                tokens=usage.total_tokens,
                cost=cost_estimate,
                response_time=response_time
            )
            
            # 构建响应
            llm_response = LLMResponse(
                content=content,
                finish_reason=finish_reason,
                model=model,
                provider=self.name,
                usage=usage,
                cost_estimate=cost_estimate,
                response_time=response_time,
                request_id=request.request_id
            )
            
            # 添加函数调用结果（如果有）
            if hasattr(choice.message, 'function_call') and choice.message.function_call:
                llm_response.function_call = choice.message.function_call.dict()
            
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                llm_response.tool_calls = [call.dict() for call in choice.message.tool_calls]
            
            return llm_response
            
        except Exception as e:
            response_time = time.time() - start_time
            self._record_request(success=False, response_time=response_time)
            
            logger.error(f"OpenAI API调用失败: {e}")
            raise RuntimeError(f"OpenAI API调用失败: {str(e)}")
    
    async def create_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str = "text-embedding-ada-002"
    ) -> Dict[str, Any]:
        """创建文本嵌入"""
        if not self.client:
            raise RuntimeError(f"提供商 {self.name} 未初始化")
        
        try:
            # 确保texts是列表格式
            if isinstance(texts, str):
                texts = [texts]
            
            # 调用嵌入API
            response = await self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            # 构建返回结果
            embeddings = [item.embedding for item in response.data]
            
            return {
                "embeddings": embeddings,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI嵌入API调用失败: {e}")
            raise RuntimeError(f"创建嵌入失败: {str(e)}")
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.client:
            return self.available_models
        
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data]
        except Exception:
            return self.available_models
    
    def _prepare_messages(self, messages) -> List[Dict[str, Any]]:
        """准备消息格式"""
        formatted_messages = []
        
        for msg in messages:
            if hasattr(msg, 'dict'):
                # Pydantic模型
                formatted_msg = msg.dict(exclude_none=True)
            elif isinstance(msg, dict):
                # 字典格式
                formatted_msg = {k: v for k, v in msg.items() if v is not None}
            else:
                raise ValueError(f"不支持的消息格式: {type(msg)}")
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    async def _health_check_test(self):
        """OpenAI健康检查测试"""
        try:
            # 使用最便宜的模型进行测试
            test_model = "gpt-4o-mini" if "gpt-4o-mini" in self.available_models else "gpt-3.5-turbo"
            
            await self.client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                temperature=0.0
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI健康检查失败: {e}")