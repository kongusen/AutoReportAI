"""
LLM健康检查服务
提供完整的LLM服务器和模型健康监控
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.models.llm_server import LLMServer, LLMModel
from app.schemas.llm_server import (
    LLMModelHealthResponse, LLMServerHealthResponse
)
from app.services.infrastructure.ai.llm.rate_limiter import get_llm_rate_limiter

logger = logging.getLogger(__name__)


class LLMHealthService:
    """LLM健康检查服务"""
    
    def __init__(self):
        self.http_timeout = 30.0
        self.test_timeout = 60.0
        
    async def test_model_health(
        self, 
        db: Session, 
        model: LLMModel, 
        test_message: str = "你好"
    ) -> LLMModelHealthResponse:
        """测试单个模型健康状态"""
        start_time = time.time()
        health_result = {
            "model_id": model.id,
            "model_name": model.name,
            "server_id": model.server_id,
            "is_healthy": False,
            "response_time": 0.0,
            "error_message": None,
            "test_response": None,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        try:
            # 获取服务器信息
            server = model.server
            if not server or not server.is_active:
                raise Exception("服务器不可用或已禁用")
            
            # 构建API请求
            headers = {
                "Content-Type": "application/json"
            }
            
            if server.api_key:
                if server.provider_type.lower() == "openai":
                    headers["Authorization"] = f"Bearer {server.api_key}"
                elif server.provider_type.lower() == "anthropic":
                    headers["x-api-key"] = server.api_key
                else:
                    headers["Authorization"] = f"Bearer {server.api_key}"
            
            # 构建请求数据
            request_data = self._build_test_request(server.provider_type, model.name, test_message)
            
            # 使用速率限制器
            rate_limiter = get_llm_rate_limiter()
            if not await rate_limiter.acquire():
                raise Exception("请求被速率限制器阻塞")
            
            try:
                # 发送HTTP请求
                async with httpx.AsyncClient(timeout=self.test_timeout) as client:
                    response = await client.post(
                        f"{server.base_url.rstrip('/')}/chat/completions",
                        json=request_data,
                        headers=headers
                    )
                    
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        test_response = self._extract_response_content(response_data)
                        
                        health_result.update({
                            "is_healthy": True,
                            "response_time": response_time,
                            "test_response": test_response
                        })
                        
                        # 更新模型状态
                        model.is_healthy = True
                        model.last_health_check = datetime.utcnow()
                        model.health_check_error = None
                        db.commit()
                        
                        # 释放速率限制器
                        rate_limiter.release(success=True, response_time=response_time)
                        
                        logger.info(f"模型健康检查成功: {model.name} ({response_time:.2f}s)")
                        
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        raise Exception(error_msg)
                        
            except Exception as e:
                rate_limiter.release(success=False)
                raise e
                
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            health_result.update({
                "is_healthy": False,
                "response_time": response_time,
                "error_message": error_message
            })
            
            # 更新模型状态
            model.is_healthy = False
            model.health_check_error = error_message
            model.last_health_check = datetime.utcnow()
            db.commit()
            
            logger.error(f"模型健康检查失败: {model.name} - {error_message}")
        
        return LLMModelHealthResponse(**health_result)
    
    async def test_server_health(
        self, 
        db: Session, 
        server: LLMServer, 
        test_message: str = "你好"
    ) -> LLMServerHealthResponse:
        """测试LLM服务器及其所有模型的健康状态"""
        start_time = time.time()
        
        # 获取服务器的所有模型
        models = db.query(LLMModel).filter(
            LLMModel.server_id == server.id,
            LLMModel.is_active == True
        ).all()
        
        model_results = []
        healthy_models = 0
        total_response_time = 0.0
        
        # 并发测试所有模型
        test_tasks = []
        for model in models:
            task = self.test_model_health(db, model, test_message)
            test_tasks.append(task)
        
        if test_tasks:
            model_results = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(model_results):
                if isinstance(result, Exception):
                    logger.error(f"模型健康检查异常: {models[i].name} - {result}")
                    continue
                
                if isinstance(result, LLMModelHealthResponse):
                    if result.is_healthy:
                        healthy_models += 1
                        total_response_time += result.response_time
        
        # 计算服务器整体健康状态
        total_models = len(models)
        health_rate = healthy_models / total_models if total_models > 0 else 0.0
        avg_response_time = total_response_time / healthy_models if healthy_models > 0 else 0.0
        overall_response_time = time.time() - start_time
        
        is_healthy = health_rate >= 0.7  # 70%以上模型健康则服务器健康
        
        # 更新服务器状态
        server.is_healthy = is_healthy
        server.last_health_check = datetime.utcnow()
        if not is_healthy:
            server.health_check_error = f"健康率过低: {health_rate:.1%}"
        else:
            server.health_check_error = None
        db.commit()
        
        return LLMServerHealthResponse(
            server_id=server.id,
            server_name=server.name,
            is_healthy=is_healthy,
            response_time=overall_response_time,
            total_models=total_models,
            healthy_models=healthy_models,
            health_rate=health_rate,
            average_model_response_time=avg_response_time,
            model_results=[
                result for result in model_results 
                if isinstance(result, LLMModelHealthResponse)
            ],
            checked_at=datetime.utcnow().isoformat(),
            error_message=server.health_check_error
        )
    
    async def test_all_servers_health(
        self, 
        db: Session, 
        test_message: str = "你好"
    ) -> List[LLMServerHealthResponse]:
        """测试所有LLM服务器的健康状态"""
        servers = db.query(LLMServer).filter(LLMServer.is_active == True).all()
        
        if not servers:
            return []
        
        # 并发测试所有服务器
        test_tasks = []
        for server in servers:
            task = self.test_server_health(db, server, test_message)
            test_tasks.append(task)
        
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        # 过滤有效结果
        health_results = []
        for result in results:
            if isinstance(result, LLMServerHealthResponse):
                health_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"服务器健康检查异常: {result}")
        
        return health_results
    
    def _build_test_request(self, provider_type: str, model_name: str, test_message: str) -> Dict[str, Any]:
        """构建测试请求数据"""
        base_request = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": test_message
                }
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        # 根据提供商类型调整请求格式
        if provider_type.lower() == "anthropic":
            # Anthropic API 格式可能略有不同
            base_request["max_tokens"] = 10
        elif provider_type.lower() == "openai":
            # OpenAI 标准格式
            pass
        else:
            # 使用通用格式
            pass
        
        return base_request
    
    def _extract_response_content(self, response_data: Dict[str, Any]) -> str:
        """提取响应内容"""
        try:
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                if "message" in choice:
                    return choice["message"].get("content", "")
                elif "text" in choice:
                    return choice["text"]
            
            return "响应格式无效"
            
        except Exception as e:
            logger.warning(f"提取响应内容失败: {e}")
            return f"解析响应失败: {str(e)}"


# 全局健康检查服务实例
_global_health_service: Optional[LLMHealthService] = None


def get_model_health_service() -> LLMHealthService:
    """获取全局模型健康检查服务"""
    global _global_health_service
    
    if _global_health_service is None:
        _global_health_service = LLMHealthService()
    
    return _global_health_service