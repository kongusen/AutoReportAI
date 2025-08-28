"""
LLM服务器客户端 - 连接到独立的LLM服务器

为IAOP平台提供统一的LLM调用接口，连接到独立的LLM服务器
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LLMClientConfig(BaseModel):
    """LLM客户端配置"""
    base_url: str = "http://localhost:8001"
    api_key: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # SSL配置
    verify_ssl: bool = False  # 默认跳过SSL验证，适用于开发环境
    
    # 连接池配置
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0


class LLMMessage(BaseModel):
    """LLM消息"""
    role: str  # system, user, assistant
    content: str


class LLMRequest(BaseModel):
    """LLM请求"""
    messages: List[LLMMessage]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
    
    # 缓存相关
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    # 提供商偏好
    provider_preference: Optional[List[str]] = None
    
    # 请求标识
    user_id: Optional[str] = None
    request_id: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM响应"""
    content: str
    model: str
    provider: str
    usage: Dict[str, Any]
    cost_estimate: Optional[float] = None
    response_time: float
    finish_reason: Optional[str] = None
    
    # 元数据
    timestamp: datetime
    request_id: Optional[str] = None
    llm_server_info: Optional[Dict[str, Any]] = None


class LLMServerClient:
    """LLM服务器客户端"""
    
    def __init__(self, config: LLMClientConfig = None, provider_type: str = "openai"):
        self.config = config or LLMClientConfig()
        self.provider_type = provider_type.lower()
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        
    async def initialize(self):
        """初始化客户端"""
        if self._initialized:
            return
        
        # 创建HTTP客户端
        limits = httpx.Limits(
            max_connections=self.config.max_connections,
            max_keepalive_connections=self.config.max_keepalive_connections,
            keepalive_expiry=self.config.keepalive_expiry
        )
        
        timeout = httpx.Timeout(self.config.timeout)
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "IAOP-LLM-Client/1.0"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        # SSL配置
        verify_ssl = self.config.verify_ssl
        if not verify_ssl and self.config.base_url.startswith('https://'):
            logger.warning(f"⚠️ SSL证书验证已禁用 - 仅用于开发环境: {self.config.base_url}")

        # 确保base_url不以斜杠结尾（httpx会自动处理路径拼接）
        clean_base_url = self.config.base_url.rstrip('/')
        
        self.client = httpx.AsyncClient(
            base_url=clean_base_url,
            headers=headers,
            timeout=timeout,
            limits=limits,
            verify=verify_ssl
        )
        
        self._initialized = True
        logger.info(f"LLM客户端已初始化，连接到: {self.config.base_url}")
        
        # 测试连接
        try:
            await self.health_check()
            logger.info("✅ LLM服务器连接测试成功")
        except Exception as e:
            logger.warning(f"⚠️ LLM服务器连接测试失败: {e}")
    
    async def chat_completion(
        self, 
        request: LLMRequest,
        timeout: Optional[int] = None
    ) -> LLMResponse:
        """发送聊天完成请求"""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # 准备请求数据 - 只包含OpenAI API标准字段
            request_data = {
                "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            }
            
            # 添加可选的标准字段，如果没有指定模型则使用默认模型
            if request.model:
                request_data["model"] = request.model
            else:
                request_data["model"] = "gpt-4o-mini"  # 默认模型
            if request.max_tokens:
                request_data["max_tokens"] = request.max_tokens
            if request.temperature is not None:
                request_data["temperature"] = request.temperature
            if request.top_p is not None:
                request_data["top_p"] = request.top_p
            if request.stream:
                request_data["stream"] = request.stream
            
            
            # 发送请求
            response = await self.client.post(
                "/chat/completions",
                json=request_data,
                timeout=timeout or self.config.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            response_time = time.time() - start_time
            
            # 根据提供商类型解析响应
            try:
                llm_response = self._parse_response(response_data, response_time)
            except Exception as parse_error:
                logger.error(f"响应解析失败: {parse_error}, 原始响应: {response_data}")
                raise RuntimeError(f"响应解析失败: {str(parse_error)}")
            
            # 更新统计
            self.successful_requests += 1
            self.total_response_time += response_time
            
            logger.debug(
                f"LLM请求成功: {llm_response.model} via {llm_response.provider} "
                f"({response_time:.2f}s, {llm_response.usage.get('total_tokens', 0)} tokens)"
            )
            
            return llm_response
            
        except httpx.HTTPStatusError as e:
            response_time = time.time() - start_time
            self.failed_requests += 1
            self.total_response_time += response_time
            
            error_detail = "未知错误"
            response_text = ""
            try:
                response_text = e.response.text
                error_data = e.response.json()
                error_detail = error_data.get("detail", error_data.get("error", str(e)))
            except:
                error_detail = str(e)
            
            logger.error(f"LLM请求HTTP错误 {e.response.status_code}: {error_detail}")
            logger.error(f"响应内容: {response_text}")
            raise RuntimeError(f"LLM服务器错误: {error_detail}")
            
        except httpx.RequestError as e:
            response_time = time.time() - start_time
            self.failed_requests += 1
            self.total_response_time += response_time
            
            logger.error(f"LLM请求连接错误: {e}")
            raise RuntimeError(f"LLM服务器连接失败: {str(e)}")
            
        except Exception as e:
            response_time = time.time() - start_time
            self.failed_requests += 1
            self.total_response_time += response_time
            
            logger.error(f"LLM请求失败: {e}")
            raise RuntimeError(f"LLM请求处理失败: {str(e)}")
    
    async def chat_completion_with_retry(
        self,
        request: LLMRequest,
        max_retries: Optional[int] = None
    ) -> LLMResponse:
        """带重试的聊天完成请求"""
        max_retries = max_retries or self.config.max_retries
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.chat_completion(request)
            except Exception as e:
                last_error = e
                
                if attempt < max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"LLM请求失败 (尝试 {attempt + 1}/{max_retries + 1}), "
                        f"{delay:.1f}秒后重试: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"LLM请求重试全部失败: {e}")
                    break
        
        raise last_error
    
    async def create_embeddings(
        self,
        texts: Union[str, List[str]], 
        model: str = "text-embedding-ada-002"
    ) -> Dict[str, Any]:
        """创建文本嵌入"""
        if not self._initialized:
            await self.initialize()
        
        try:
            request_data = {
                "input": texts if isinstance(texts, list) else [texts],
                "model": model
            }
            
            response = await self.client.post(
                "/embeddings",
                json=request_data
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"嵌入创建失败: {e}")
            raise RuntimeError(f"嵌入创建失败: {str(e)}")
    
    async def get_available_providers(self) -> List[Dict[str, Any]]:
        """获取可用的LLM提供商"""
        if not self._initialized:
            await self.initialize()
        
        try:
            response = await self.client.get("/providers")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取提供商列表失败: {e}")
            return []
    
    async def get_provider_models(self, provider_name: str) -> List[str]:
        """获取指定提供商的模型列表"""
        if not self._initialized:
            await self.initialize()
        
        try:
            response = await self.client.get(f"/providers/{provider_name}/models")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"获取提供商 {provider_name} 模型列表失败: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self._initialized:
            await self.initialize()
        
        # 先尝试标准的健康检查端点
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info("健康检查端点不存在，尝试模型列表端点")
            else:
                logger.warning(f"健康检查端点错误: {e}")
        except Exception as e:
            logger.warning(f"健康检查端点连接失败: {e}")
        
        # 回退到模型列表检查
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            models_data = response.json()
            
            # 如果能获取到模型列表，说明服务器基本可用
            models = models_data.get('data', []) if isinstance(models_data, dict) else []
            return {
                "status": "healthy",
                "method": "models_fallback",
                "models_count": len(models),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"模型列表健康检查也失败: {e}")
            raise RuntimeError(f"LLM服务器不可用: {str(e)}")
    
    async def test_model_health(
        self, 
        model: str, 
        test_message: str = "你好", 
        timeout: Optional[int] = 10
    ) -> Dict[str, Any]:
        """测试模型健康状态
        
        Args:
            model: 模型名称
            test_message: 测试消息，默认为"你好"
            timeout: 超时时间（秒）
            
        Returns:
            包含健康检查结果的字典
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 构建测试请求
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content=test_message)],
                model=model,
                max_tokens=50,
                temperature=0.1  # 使用低温度以获得稳定输出
            )
            
            # 发送请求
            response = await self.chat_completion(test_request)
            response_time = time.time() - start_time
            
            # 判断响应是否有效
            is_healthy = bool(response.content and response.content.strip())
            
            result = {
                "is_healthy": is_healthy,
                "response_time_ms": response_time * 1000,
                "test_message": test_message,
                "response_content": response.content if is_healthy else None,
                "model": response.model,
                "provider": response.provider,
                "error_message": None if is_healthy else "模型无响应或响应为空"
            }
            
            logger.info(f"模型 {model} 健康检查{'通过' if is_healthy else '失败'}: {response_time:.2f}s")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            logger.error(f"模型 {model} 健康检查失败: {error_message}")
            
            return {
                "is_healthy": False,
                "response_time_ms": response_time * 1000,
                "test_message": test_message,
                "response_content": None,
                "model": model,
                "provider": "unknown",
                "error_message": error_message
            }
    
    async def get_usage_stats(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """获取使用统计"""
        if not self._initialized:
            await self.initialize()
        
        try:
            response = await self.client.get(
                f"/usage/{user_id}",
                params={"hours": hours}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return {}
    
    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        avg_response_time = (
            self.total_response_time / self.total_requests
            if self.total_requests > 0 else 0.0
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
            "avg_response_time": avg_response_time,
            "server_url": self.config.base_url,
            "initialized": self._initialized
        }
    
    async def cleanup(self):
        """清理客户端资源"""
        if self.client:
            await self.client.aclose()
            self.client = None
        
        self._initialized = False
        logger.info("LLM客户端已清理")
    
    def _parse_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """根据提供商类型解析响应"""
        if self.provider_type == "openai":
            return self._parse_openai_response(response_data, response_time)
        elif self.provider_type == "anthropic":
            return self._parse_anthropic_response(response_data, response_time)
        elif self.provider_type == "google":
            return self._parse_google_response(response_data, response_time)
        elif self.provider_type == "cohere":
            return self._parse_cohere_response(response_data, response_time)
        elif self.provider_type == "huggingface":
            return self._parse_huggingface_response(response_data, response_time)
        else:
            # 默认使用OpenAI格式
            return self._parse_openai_response(response_data, response_time)
    
    def _parse_openai_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """解析OpenAI格式响应"""
        # 提取消息内容
        choices = response_data.get("choices", [])
        content = ""
        finish_reason = None
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            finish_reason = choices[0].get("finish_reason")
        
        return LLMResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider=self.provider_type,
            usage=response_data.get("usage", {}),
            response_time=response_time,
            finish_reason=finish_reason,
            timestamp=datetime.utcnow(),
            request_id=response_data.get("id"),
            llm_server_info={
                "server_url": self.config.base_url,
                "raw_response": response_data
            }
        )
    
    def _parse_anthropic_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """解析Anthropic格式响应"""
        # Anthropic API响应格式
        content = response_data.get("content", [])
        text_content = ""
        if content and isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    text_content = item.get("text", "")
                    break
        
        return LLMResponse(
            content=text_content,
            model=response_data.get("model", "unknown"),
            provider="anthropic",
            usage=response_data.get("usage", {}),
            response_time=response_time,
            finish_reason=response_data.get("stop_reason"),
            timestamp=datetime.utcnow(),
            request_id=response_data.get("id"),
            llm_server_info={
                "server_url": self.config.base_url,
                "raw_response": response_data
            }
        )
    
    def _parse_google_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """解析Google格式响应"""
        # Google Gemini API响应格式
        candidates = response_data.get("candidates", [])
        content = ""
        finish_reason = None
        if candidates:
            candidate = candidates[0]
            content_parts = candidate.get("content", {}).get("parts", [])
            if content_parts:
                content = content_parts[0].get("text", "")
            finish_reason = candidate.get("finishReason")
        
        return LLMResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider="google",
            usage=response_data.get("usageMetadata", {}),
            response_time=response_time,
            finish_reason=finish_reason,
            timestamp=datetime.utcnow(),
            request_id=None,  # Google API可能没有request_id
            llm_server_info={
                "server_url": self.config.base_url,
                "raw_response": response_data
            }
        )
    
    def _parse_cohere_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """解析Cohere格式响应"""
        # Cohere API响应格式
        content = response_data.get("text", "")
        
        return LLMResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider="cohere",
            usage=response_data.get("meta", {}),
            response_time=response_time,
            finish_reason=response_data.get("finish_reason"),
            timestamp=datetime.utcnow(),
            request_id=response_data.get("generation_id"),
            llm_server_info={
                "server_url": self.config.base_url,
                "raw_response": response_data
            }
        )
    
    def _parse_huggingface_response(self, response_data: Dict[str, Any], response_time: float) -> LLMResponse:
        """解析HuggingFace格式响应"""
        # HuggingFace API响应格式可能多样，通常是一个列表
        content = ""
        if isinstance(response_data, list) and response_data:
            content = response_data[0].get("generated_text", "")
        elif isinstance(response_data, dict):
            content = response_data.get("generated_text", response_data.get("text", ""))
        
        return LLMResponse(
            content=content,
            model="huggingface-model",
            provider="huggingface",
            usage={},
            response_time=response_time,
            finish_reason=None,
            timestamp=datetime.utcnow(),
            request_id=None,
            llm_server_info={
                "server_url": self.config.base_url,
                "raw_response": response_data
            }
        )


# 全局客户端实例
_global_llm_client: Optional[LLMServerClient] = None

def get_llm_client(config: LLMClientConfig = None) -> LLMServerClient:
    """获取全局LLM客户端实例"""
    global _global_llm_client
    if _global_llm_client is None:
        # 如果没有提供配置，尝试从数据库获取健康的LLM服务器配置
        if config is None:
            config = _get_llm_config_from_database()
        _global_llm_client = LLMServerClient(config)
    return _global_llm_client

def _get_llm_config_from_database() -> LLMClientConfig:
    """从数据库获取LLM服务器配置"""
    try:
        from app.db.session import SessionLocal
        from app.crud.crud_llm_server import crud_llm_server
        
        db = SessionLocal()
        try:
            # 获取健康的服务器
            healthy_servers = crud_llm_server.get_healthy_servers(db)
            if healthy_servers:
                server = healthy_servers[0]  # 使用第一个健康的服务器
                logger.info(f"使用数据库配置的LLM服务器: {server.name} ({server.base_url})")
                return LLMClientConfig(
                    base_url=server.base_url,
                    api_key=server.api_key,
                    timeout=server.timeout_seconds,
                    max_retries=server.max_retries,
                )
            else:
                # 获取活跃的服务器（即使不健康）
                active_servers = crud_llm_server.get_active_servers(db)
                if active_servers:
                    server = active_servers[0]
                    logger.warning(f"使用不健康的LLM服务器: {server.name} ({server.base_url})")
                    return LLMClientConfig(
                        base_url=server.base_url,
                        api_key=server.api_key,
                        timeout=server.timeout_seconds,
                        max_retries=server.max_retries,
                    )
                
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"从数据库获取LLM配置失败: {e}，使用默认配置")
    
    # 如果无法从数据库获取配置，使用默认配置
    logger.warning("使用默认LLM配置: localhost:8001")
    return LLMClientConfig()

def reset_llm_client():
    """重置全局LLM客户端，下次调用时会重新初始化"""
    global _global_llm_client
    if _global_llm_client:
        # 如果需要，可以在这里调用cleanup
        _global_llm_client = None
        logger.info("全局LLM客户端已重置")


# 便捷函数
async def call_llm(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    user_id: Optional[str] = None,
    provider_preference: Optional[List[str]] = None
) -> str:
    """便捷的LLM调用函数
    
    Args:
        messages: 消息列表，格式: [{"role": "user", "content": "..."}]
        model: 指定模型
        max_tokens: 最大token数
        temperature: 温度参数
        user_id: 用户ID
        provider_preference: 提供商偏好
        
    Returns:
        LLM响应内容
    """
    client = get_llm_client()
    
    # 转换消息格式
    llm_messages = [LLMMessage(role=msg["role"], content=msg["content"]) for msg in messages]
    
    request = LLMRequest(
        messages=llm_messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        user_id=user_id,
        provider_preference=provider_preference
    )
    
    response = await client.chat_completion_with_retry(request)
    return response.content


async def call_llm_with_system_prompt(
    system_prompt: str,
    user_message: str,
    **kwargs
) -> str:
    """带系统提示的LLM调用
    
    Args:
        system_prompt: 系统提示
        user_message: 用户消息
        **kwargs: 其他参数传递给call_llm
        
    Returns:
        LLM响应内容
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    return await call_llm(messages, **kwargs)