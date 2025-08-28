"""
LLM管理器 - 统一管理多个LLM提供商

负责：
1. 多提供商的统一接口
2. 智能负载均衡和故障转移
3. 模型选择和优化
4. 连接池管理
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from .models import (
    LLMRequest, 
    LLMResponse, 
    LLMProvider,
    ProviderConfig,
    HealthStatus,
    UsageInfo
)
from .providers import (
    OpenAIProvider,
    AnthropicProvider, 
    GoogleProvider,
    OllamaProvider,
    get_provider_class
)
from .load_balancer import LoadBalancer
from .config import get_config

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM管理器 - 统一管理多个LLM提供商"""
    
    def __init__(self):
        self.providers: Dict[str, Any] = {}  # 提供商实例
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.load_balancer = LoadBalancer()
        self.config = get_config()
        self._initialized = False
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = datetime.utcnow()
        
    async def initialize(self):
        """初始化所有配置的提供商"""
        if self._initialized:
            return
            
        logger.info("初始化LLM管理器...")
        
        # 从配置加载提供商
        for provider_name, config in self.config.providers.items():
            try:
                await self._initialize_provider(provider_name, config)
                logger.info(f"✅ 提供商 {provider_name} 初始化成功")
            except Exception as e:
                logger.error(f"❌ 提供商 {provider_name} 初始化失败: {e}")
        
        # 初始化负载均衡器
        available_providers = list(self.providers.keys())
        self.load_balancer.initialize(available_providers)
        
        self._initialized = True
        logger.info(f"LLM管理器初始化完成，可用提供商: {available_providers}")
    
    async def _initialize_provider(self, name: str, config: ProviderConfig):
        """初始化单个提供商"""
        provider_class = get_provider_class(config.type)
        if not provider_class:
            raise ValueError(f"不支持的提供商类型: {config.type}")
        
        provider = provider_class(name, config)
        await provider.initialize()
        
        self.providers[name] = provider
        self.provider_configs[name] = config
    
    async def chat_completion(
        self, 
        request: LLMRequest, 
        user_id: str,
        provider_preference: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        聊天完成 - 统一接口
        
        Args:
            request: LLM请求
            user_id: 用户ID
            provider_preference: 提供商偏好顺序
            
        Returns:
            LLM响应
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        # 确定要尝试的提供商顺序
        if provider_preference:
            provider_order = [p for p in provider_preference if p in self.providers]
        else:
            provider_order = self.load_balancer.get_provider_order(
                user_id=user_id,
                model_preference=request.model
            )
        
        if not provider_order:
            raise RuntimeError("没有可用的LLM提供商")
        
        last_error = None
        
        # 尝试每个提供商
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
                
            try:
                logger.info(f"尝试使用提供商: {provider_name}")
                
                # 调用提供商
                response = await provider.chat_completion(request)
                
                # 更新统计
                self.total_requests += 1
                self.successful_requests += 1
                
                # 更新负载均衡器
                duration = time.time() - start_time
                await self.load_balancer.record_success(
                    provider_name, 
                    duration,
                    response.usage.get("total_tokens", 0)
                )
                
                # 添加管理信息到响应
                response.provider = provider_name
                response.llm_server_info = {
                    "server_version": "1.0.0",
                    "processing_time": duration,
                    "user_id": user_id,
                    "provider_order": provider_order
                }
                
                return response
                
            except Exception as e:
                logger.warning(f"提供商 {provider_name} 调用失败: {e}")
                last_error = e
                
                # 记录失败
                duration = time.time() - start_time
                await self.load_balancer.record_failure(provider_name, str(e), duration)
                
                continue
        
        # 所有提供商都失败了
        self.total_requests += 1
        self.failed_requests += 1
        
        raise RuntimeError(
            f"所有LLM提供商都不可用。最后错误: {last_error}"
        )
    
    async def create_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str = "text-embedding-ada-002",
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """创建文本嵌入"""
        if not self._initialized:
            await self.initialize()
        
        # 优先选择支持嵌入的提供商
        embedding_providers = [
            name for name, provider in self.providers.items()
            if hasattr(provider, 'create_embeddings') and provider.supports_embeddings
        ]
        
        if not embedding_providers:
            raise RuntimeError("没有支持嵌入功能的提供商")
        
        # 使用第一个可用的嵌入提供商
        provider_name = embedding_providers[0]
        provider = self.providers[provider_name]
        
        try:
            result = await provider.create_embeddings(texts, model)
            return result
        except Exception as e:
            logger.error(f"嵌入创建失败: {e}")
            raise
    
    async def get_provider_list(self) -> List[LLMProvider]:
        """获取提供商列表"""
        if not self._initialized:
            await self.initialize()
        
        providers = []
        for name, provider in self.providers.items():
            config = self.provider_configs[name]
            
            # 获取提供商状态
            health = await provider.health_check() if hasattr(provider, 'health_check') else {"status": "unknown"}
            
            providers.append(LLMProvider(
                name=name,
                type=config.type,
                status=health.get("status", "unknown"),
                models=getattr(provider, 'available_models', []),
                capabilities=getattr(provider, 'capabilities', []),
                cost_info=getattr(provider, 'cost_info', {}),
                rate_limits=getattr(provider, 'rate_limits', {}),
                metadata={
                    "initialized": True,
                    "config": config.dict(exclude={"api_key"})  # 不包含敏感信息
                }
            ))
        
        return providers
    
    async def get_provider_models(self, provider_name: str) -> List[str]:
        """获取提供商的可用模型"""
        if provider_name not in self.providers:
            raise ValueError(f"提供商不存在: {provider_name}")
        
        provider = self.providers[provider_name]
        
        if hasattr(provider, 'get_available_models'):
            return await provider.get_available_models()
        else:
            return getattr(provider, 'available_models', [])
    
    async def update_provider_config(
        self, 
        provider_name: str, 
        new_config: ProviderConfig
    ):
        """更新提供商配置"""
        if provider_name not in self.providers:
            raise ValueError(f"提供商不存在: {provider_name}")
        
        # 重新初始化提供商
        try:
            # 停止旧提供商
            old_provider = self.providers[provider_name]
            if hasattr(old_provider, 'cleanup'):
                await old_provider.cleanup()
            
            # 初始化新提供商
            await self._initialize_provider(provider_name, new_config)
            
            logger.info(f"提供商 {provider_name} 配置已更新")
            
        except Exception as e:
            logger.error(f"更新提供商配置失败: {e}")
            raise
    
    async def health_check(self) -> HealthStatus:
        """系统健康检查"""
        if not self._initialized:
            return HealthStatus(
                status="not_initialized",
                message="LLM管理器尚未初始化",
                providers={},
                uptime=0,
                total_requests=0,
                success_rate=0.0
            )
        
        # 检查所有提供商健康状况
        provider_health = {}
        healthy_count = 0
        
        for name, provider in self.providers.items():
            try:
                if hasattr(provider, 'health_check'):
                    health = await provider.health_check()
                else:
                    health = {"status": "unknown", "message": "健康检查不支持"}
                
                provider_health[name] = health
                if health.get("status") == "healthy":
                    healthy_count += 1
                    
            except Exception as e:
                provider_health[name] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # 计算整体状态
        total_providers = len(self.providers)
        if total_providers == 0:
            overall_status = "no_providers"
        elif healthy_count == total_providers:
            overall_status = "healthy"
        elif healthy_count > 0:
            overall_status = "partial"
        else:
            overall_status = "unhealthy"
        
        # 计算成功率
        success_rate = (
            self.successful_requests / self.total_requests 
            if self.total_requests > 0 else 0.0
        )
        
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return HealthStatus(
            status=overall_status,
            message=f"{healthy_count}/{total_providers} 提供商健康",
            providers=provider_health,
            uptime=uptime,
            total_requests=self.total_requests,
            success_rate=success_rate,
            metadata={
                "load_balancer_stats": self.load_balancer.get_stats(),
                "failed_requests": self.failed_requests,
                "start_time": self.start_time.isoformat()
            }
        )
    
    async def test_provider_connection(self, provider_name: str) -> Dict[str, Any]:
        """测试提供商连接"""
        if provider_name not in self.providers:
            raise ValueError(f"提供商不存在: {provider_name}")
        
        provider = self.providers[provider_name]
        
        try:
            # 发送测试请求
            test_request = LLMRequest(
                messages=[{"role": "user", "content": "Hello, this is a connection test."}],
                max_tokens=5,
                temperature=0.0
            )
            
            start_time = time.time()
            response = await provider.chat_completion(test_request)
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "provider": provider_name,
                "response_time": duration,
                "model": response.model,
                "cost_estimate": response.cost_estimate,
                "message": "连接测试成功"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "provider": provider_name,
                "error": str(e),
                "message": "连接测试失败"
            }
    
    def get_available_providers(self) -> List[str]:
        """获取可用提供商列表"""
        return list(self.providers.keys())
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理LLM管理器...")
        
        for name, provider in self.providers.items():
            try:
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
                logger.info(f"✅ 提供商 {name} 已清理")
            except Exception as e:
                logger.error(f"❌ 清理提供商 {name} 失败: {e}")
        
        self.providers.clear()
        self.provider_configs.clear()
        self._initialized = False
        
        logger.info("LLM管理器清理完成")


# 全局LLM管理器实例
_global_llm_manager: Optional[LLMManager] = None

def get_llm_manager() -> LLMManager:
    """获取全局LLM管理器实例"""
    global _global_llm_manager
    if _global_llm_manager is None:
        _global_llm_manager = LLMManager()
    return _global_llm_manager