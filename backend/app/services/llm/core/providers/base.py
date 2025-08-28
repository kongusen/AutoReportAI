"""
基础LLM提供商抽象类

定义所有LLM提供商必须实现的接口
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..models import LLMRequest, LLMResponse, ProviderConfig, UsageInfo

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """基础LLM提供商抽象类"""
    
    def __init__(self, name: str, config: ProviderConfig):
        self.name = name
        self.config = config
        self.initialized = False
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.response_times = []
        
        # 能力标识
        self.supports_chat = True
        self.supports_embeddings = False
        self.supports_functions = False
        self.supports_streaming = False
        
        # 可用模型列表
        self.available_models: List[str] = []
        
        # 成本信息（每1K tokens的价格）
        self.cost_info: Dict[str, Dict[str, float]] = {}
        
        # 速率限制信息
        self.rate_limits = {
            "requests_per_minute": config.max_requests_per_minute,
            "tokens_per_minute": config.max_tokens_per_minute
        }
        
    async def initialize(self):
        """初始化提供商"""
        if self.initialized:
            return
            
        try:
            await self._initialize()
            self.initialized = True
            logger.info(f"提供商 {self.name} 初始化成功")
        except Exception as e:
            logger.error(f"提供商 {self.name} 初始化失败: {e}")
            raise
    
    @abstractmethod
    async def _initialize(self):
        """具体的初始化实现 - 子类必须实现"""
        pass
    
    @abstractmethod
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """聊天完成 - 子类必须实现"""
        pass
    
    async def create_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str = None
    ) -> Dict[str, Any]:
        """创建嵌入 - 子类可选实现"""
        if not self.supports_embeddings:
            raise NotImplementedError(f"提供商 {self.name} 不支持嵌入功能")
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return self.available_models
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.initialized:
            return {
                "status": "not_initialized",
                "message": "提供商未初始化"
            }
        
        try:
            # 发送简单的测试请求
            start_time = time.time()
            await self._health_check_test()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "message": "提供商运行正常",
                "statistics": self._get_statistics()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "error_type": type(e).__name__
            }
    
    async def _health_check_test(self):
        """健康检查测试 - 子类可以重写"""
        # 默认实现：发送简单的聊天请求
        test_request = LLMRequest(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            temperature=0.0
        )
        await self.chat_completion(test_request)
    
    def _record_request(self, success: bool, tokens: int = 0, cost: float = 0.0, response_time: float = 0.0):
        """记录请求统计"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.total_tokens += tokens
            self.total_cost += cost
            self.response_times.append(response_time)
            
            # 只保留最近100次的响应时间
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
        else:
            self.failed_requests += 1
    
    def _get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0.0
        )
        
        success_rate = (
            self.successful_requests / self.total_requests
            if self.total_requests > 0 else 0.0
        )
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_response_time": avg_response_time,
            "available_models": len(self.available_models)
        }
    
    def _estimate_cost(self, model: str, usage: UsageInfo) -> float:
        """估算成本"""
        if model not in self.cost_info:
            return 0.0
            
        costs = self.cost_info[model]
        
        input_cost = (usage.prompt_tokens / 1000) * costs.get("input", 0)
        output_cost = (usage.completion_tokens / 1000) * costs.get("output", 0)
        
        return input_cost + output_cost
    
    def _create_usage_info(self, prompt_tokens: int, completion_tokens: int) -> UsageInfo:
        """创建使用信息"""
        return UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    def _validate_request(self, request: LLMRequest):
        """验证请求参数"""
        if not request.messages:
            raise ValueError("messages不能为空")
        
        if request.max_tokens and request.max_tokens > 32000:
            raise ValueError("max_tokens不能超过32000")
        
        if request.temperature and (request.temperature < 0 or request.temperature > 2):
            raise ValueError("temperature必须在0-2之间")
    
    async def cleanup(self):
        """清理资源"""
        logger.info(f"清理提供商 {self.name} 的资源...")
        # 子类可以重写这个方法来清理特定资源