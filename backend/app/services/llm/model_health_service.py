"""
模型健康检查服务

提供模型健康状态测试和管理功能
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.crud.crud_llm_server import crud_llm_server
from app.models.llm_server import LLMServer, LLMModel
from app.schemas.llm_server import LLMModelHealthResponse, LLMServerHealthResponse
from .client import LLMServerClient, LLMClientConfig

logger = logging.getLogger(__name__)


class ModelHealthService:
    """模型健康检查服务"""
    
    def __init__(self):
        self._clients: Dict[int, LLMServerClient] = {}  # server_id -> client
    
    def _get_client(self, server: LLMServer) -> LLMServerClient:
        """获取或创建LLM客户端"""
        if server.id not in self._clients:
            config = LLMClientConfig(
                base_url=server.base_url,
                api_key=server.api_key if server.auth_enabled else None,
                timeout=server.timeout_seconds,
                max_retries=server.max_retries
            )
            provider_type = getattr(server, 'provider_type', 'openai')
            self._clients[server.id] = LLMServerClient(config, provider_type)
        
        return self._clients[server.id]
    
    async def test_model_health(
        self,
        db: Session,
        model: LLMModel,
        test_message: str = "你好"
    ) -> LLMModelHealthResponse:
        """测试单个模型的健康状态"""
        start_time = datetime.utcnow()
        
        try:
            # 获取服务器信息
            server = db.query(LLMServer).filter(LLMServer.id == model.server_id).first()
            if not server:
                raise RuntimeError(f"服务器 {model.server_id} 不存在")
            
            if not server.is_active:
                raise RuntimeError(f"服务器 {server.name} 未激活")
            
            # 获取客户端并测试
            client = self._get_client(server)
            result = await client.test_model_health(
                model=model.name,
                test_message=test_message
            )
            
            # 更新模型健康状态
            model.is_healthy = result["is_healthy"]
            model.last_health_check = start_time
            model.health_check_message = result.get("error_message") or "健康检查通过"
            db.commit()
            
            # 构建响应
            response = LLMModelHealthResponse(
                model_id=model.id,
                model_name=model.name,
                is_healthy=result["is_healthy"],
                response_time_ms=result["response_time_ms"],
                test_message=test_message,
                response_content=result.get("response_content"),
                error_message=result.get("error_message"),
                last_check=start_time
            )
            
            logger.info(f"模型 {model.name} 健康检查完成: {'✅通过' if result['is_healthy'] else '❌失败'}")
            return response
            
        except Exception as e:
            # 更新为不健康状态
            model.is_healthy = False
            model.last_health_check = start_time
            model.health_check_message = str(e)
            db.commit()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            response = LLMModelHealthResponse(
                model_id=model.id,
                model_name=model.name,
                is_healthy=False,
                response_time_ms=response_time,
                test_message=test_message,
                response_content=None,
                error_message=str(e),
                last_check=start_time
            )
            
            logger.error(f"模型 {model.name} 健康检查失败: {e}")
            return response
    
    async def test_server_health(
        self,
        db: Session,
        server: LLMServer,
        test_message: str = "你好",
        test_all_models: bool = True
    ) -> LLMServerHealthResponse:
        """测试服务器及其所有模型的健康状态"""
        start_time = datetime.utcnow()
        
        # 获取服务器的所有活跃模型
        models = db.query(LLMModel).filter(
            LLMModel.server_id == server.id,
            LLMModel.is_active == True
        ).all()
        
        model_results: List[LLMModelHealthResponse] = []
        healthy_count = 0
        total_response_time = 0.0
        
        if test_all_models and models:
            # 并行测试所有模型
            tasks = [
                self.test_model_health(db, model, test_message)
                for model in models
            ]
            
            model_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            valid_results = []
            for i, result in enumerate(model_results):
                if isinstance(result, Exception):
                    # 处理异常情况
                    model = models[i]
                    result = LLMModelHealthResponse(
                        model_id=model.id,
                        model_name=model.name,
                        is_healthy=False,
                        response_time_ms=0.0,
                        test_message=test_message,
                        response_content=None,
                        error_message=str(result),
                        last_check=start_time
                    )
                
                valid_results.append(result)
                if result.is_healthy:
                    healthy_count += 1
                total_response_time += result.response_time_ms
            
            model_results = valid_results
        
        # 更新服务器健康状态
        server_is_healthy = healthy_count > 0 if models else False
        avg_response_time = total_response_time / len(models) if models else 0.0
        
        server.is_healthy = server_is_healthy
        server.last_health_check = start_time
        db.commit()
        
        response = LLMServerHealthResponse(
            server_id=server.id,
            server_name=server.name,
            is_healthy=server_is_healthy,
            healthy_models=healthy_count,
            total_models=len(models),
            response_time_ms=avg_response_time,
            last_check=start_time,
            models=model_results
        )
        
        logger.info(
            f"服务器 {server.name} 健康检查完成: "
            f"{'✅健康' if server_is_healthy else '❌不健康'} "
            f"({healthy_count}/{len(models)} 模型正常)"
        )
        
        return response
    
    async def test_all_servers_health(
        self,
        db: Session,
        test_message: str = "你好"
    ) -> List[LLMServerHealthResponse]:
        """测试所有活跃服务器的健康状态"""
        servers = db.query(LLMServer).filter(LLMServer.is_active == True).all()
        
        if not servers:
            logger.warning("没有找到活跃的LLM服务器")
            return []
        
        # 并行测试所有服务器
        tasks = [
            self.test_server_health(db, server, test_message)
            for server in servers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                server = servers[i]
                result = LLMServerHealthResponse(
                    server_id=server.id,
                    server_name=server.name,
                    is_healthy=False,
                    healthy_models=0,
                    total_models=0,
                    response_time_ms=0.0,
                    last_check=datetime.utcnow(),
                    models=[]
                )
                logger.error(f"服务器 {server.name} 健康检查异常: {result}")
            
            valid_results.append(result)
        
        total_servers = len(servers)
        healthy_servers = sum(1 for r in valid_results if r.is_healthy)
        
        logger.info(f"所有服务器健康检查完成: {healthy_servers}/{total_servers} 服务器正常")
        
        return valid_results
    
    async def cleanup(self):
        """清理资源"""
        for client in self._clients.values():
            await client.cleanup()
        self._clients.clear()
        logger.info("模型健康检查服务已清理")


# 全局服务实例
_global_health_service: Optional[ModelHealthService] = None

def get_model_health_service() -> ModelHealthService:
    """获取全局模型健康检查服务实例"""
    global _global_health_service
    if _global_health_service is None:
        _global_health_service = ModelHealthService()
    return _global_health_service