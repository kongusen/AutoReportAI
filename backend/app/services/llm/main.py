#!/usr/bin/env python3
"""
独立LLM服务器 - 专门提供大语言模型推理服务

提供统一的LLM API接口，支持多种模型提供商：
- OpenAI (GPT系列)
- Anthropic (Claude系列) 
- Google (Gemini系列)
- 本地模型 (Ollama等)

主要功能：
1. 统一的LLM调用接口
2. 智能负载均衡和故障转移
3. Token使用量统计和成本估算
4. 请求缓存和性能优化
5. 用户认证和权限管理
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# LLM服务核心组件
from core.llm_manager import LLMManager, get_llm_manager
from core.models import (
    LLMRequest, 
    LLMResponse, 
    LLMProvider,
    ProviderConfig,
    UsageStats,
    HealthStatus,
    ErrorResponse
)
from core.auth import authenticate_request, get_current_user
from core.cache import LLMCacheManager, get_cache_manager
from core.metrics import MetricsCollector, get_metrics_collector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm-server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 启动独立LLM服务器...")
    
    # 初始化LLM管理器
    llm_manager = get_llm_manager()
    await llm_manager.initialize()
    logger.info(f"✅ 初始化 {len(llm_manager.get_available_providers())} 个LLM提供商")
    
    # 初始化缓存管理器
    cache_manager = get_cache_manager()
    await cache_manager.initialize()
    logger.info("✅ 缓存系统已初始化")
    
    # 初始化指标收集器
    metrics_collector = get_metrics_collector()
    await metrics_collector.start()
    logger.info("✅ 指标收集系统已启动")
    
    logger.info("🎉 LLM服务器启动完成！")
    
    yield
    
    # 关闭时清理
    logger.info("🛑 正在关闭LLM服务器...")
    await metrics_collector.stop()
    await cache_manager.cleanup()
    await llm_manager.cleanup()
    logger.info("✅ LLM服务器已安全关闭")


# 创建FastAPI应用
app = FastAPI(
    title="独立LLM服务器",
    description="专门提供大语言模型推理服务的独立服务器",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# === 核心API端点 ===

@app.post("/v1/chat/completions", response_model=LLMResponse)
async def chat_completions(
    request: LLMRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    llm_manager: LLMManager = Depends(get_llm_manager),
    cache_manager: LLMCacheManager = Depends(get_cache_manager),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """
    统一的聊天完成接口 - 兼容OpenAI API格式
    
    支持多个LLM提供商的统一调用接口，自动处理：
    - 提供商选择和故障转移
    - 请求缓存和去重
    - Token使用统计
    - 性能监控
    """
    start_time = datetime.utcnow()
    
    try:
        # 记录请求开始
        await metrics.record_request_start(user_id, request.model or "default")
        
        # 检查缓存
        cache_key = cache_manager.generate_cache_key(request, user_id)
        cached_response = await cache_manager.get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"缓存命中: {cache_key}")
            await metrics.record_cache_hit(user_id)
            return cached_response
        
        # 调用LLM服务
        response = await llm_manager.chat_completion(request, user_id)
        
        # 缓存响应
        if request.cache_enabled:
            background_tasks.add_task(
                cache_manager.cache_response, 
                cache_key, 
                response, 
                ttl=request.cache_ttl
            )
        
        # 记录成功指标
        duration = (datetime.utcnow() - start_time).total_seconds()
        await metrics.record_successful_request(
            user_id, 
            response.provider, 
            response.model,
            response.usage.get("total_tokens", 0),
            duration,
            response.cost_estimate or 0.0
        )
        
        return response
        
    except Exception as e:
        # 记录失败指标
        duration = (datetime.utcnow() - start_time).total_seconds()
        await metrics.record_failed_request(user_id, str(e), duration)
        
        logger.error(f"LLM请求失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=str(e),
                error_type=type(e).__name__,
                error_code="LLM_REQUEST_FAILED"
            ).dict()
        )


@app.post("/v1/embeddings")
async def create_embeddings(
    request: Dict[str, Any],
    user_id: str = Depends(get_current_user),
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """创建文本嵌入向量"""
    try:
        result = await llm_manager.create_embeddings(
            texts=request.get("input", []),
            model=request.get("model", "text-embedding-ada-002"),
            user_id=user_id
        )
        return result
    except Exception as e:
        logger.error(f"嵌入创建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === 管理API端点 ===

@app.get("/v1/providers", response_model=List[LLMProvider])
async def list_providers(
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """获取所有可用的LLM提供商列表"""
    return await llm_manager.get_provider_list()


@app.get("/v1/providers/{provider_name}/models")
async def list_provider_models(
    provider_name: str,
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """获取指定提供商的可用模型列表"""
    try:
        models = await llm_manager.get_provider_models(provider_name)
        return {"models": models}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/providers/{provider_name}/config")
async def update_provider_config(
    provider_name: str,
    config: ProviderConfig,
    user_id: str = Depends(authenticate_request),  # 需要管理员权限
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """更新提供商配置"""
    try:
        await llm_manager.update_provider_config(provider_name, config)
        return {"message": f"提供商 {provider_name} 配置已更新"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# === 监控和统计API ===

@app.get("/v1/health", response_model=HealthStatus)
async def health_check(
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """系统健康检查"""
    return await llm_manager.health_check()


@app.get("/v1/usage/{user_id}", response_model=UsageStats)
async def get_user_usage(
    user_id: str,
    hours: int = 24,
    current_user: str = Depends(get_current_user),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """获取用户使用统计"""
    # 权限检查：用户只能查看自己的统计，管理员可以查看所有
    if current_user != user_id and not await authenticate_request(current_user):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return await metrics.get_user_usage_stats(user_id, hours)


@app.get("/v1/stats/global")
async def get_global_stats(
    hours: int = 24,
    _: str = Depends(authenticate_request),  # 需要管理员权限
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """获取全局使用统计"""
    return await metrics.get_global_stats(hours)


@app.post("/v1/cache/clear")
async def clear_cache(
    user_id: Optional[str] = None,
    _: str = Depends(authenticate_request),  # 需要管理员权限
    cache_manager: LLMCacheManager = Depends(get_cache_manager)
):
    """清理缓存"""
    if user_id:
        await cache_manager.clear_user_cache(user_id)
        return {"message": f"用户 {user_id} 的缓存已清理"}
    else:
        await cache_manager.clear_all_cache()
        return {"message": "所有缓存已清理"}


# === 调试和开发API ===

@app.get("/v1/debug/config")
async def get_debug_config(
    _: str = Depends(authenticate_request)  # 需要管理员权限
):
    """获取调试配置信息"""
    return {
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": logging.getLogger().level,
        "providers_count": len(get_llm_manager().get_available_providers()),
        "cache_enabled": get_cache_manager().is_enabled(),
        "metrics_enabled": get_metrics_collector().is_enabled()
    }


@app.post("/v1/debug/test-provider/{provider_name}")
async def test_provider(
    provider_name: str,
    _: str = Depends(authenticate_request),
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """测试指定提供商的连接"""
    try:
        result = await llm_manager.test_provider_connection(provider_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# === 错误处理 ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.utcnow().isoformat()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# === 服务器配置 ===

def get_server_config():
    """获取服务器配置"""
    return {
        "host": os.getenv("LLM_SERVER_HOST", "0.0.0.0"),
        "port": int(os.getenv("LLM_SERVER_PORT", "8001")),
        "workers": int(os.getenv("LLM_SERVER_WORKERS", "1")),
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "reload": os.getenv("ENVIRONMENT") == "development"
    }


if __name__ == "__main__":
    config = get_server_config()
    
    logger.info(f"🚀 启动独立LLM服务器")
    logger.info(f"📍 地址: http://{config['host']}:{config['port']}")
    logger.info(f"📖 API文档: http://{config['host']}:{config['port']}/docs")
    
    uvicorn.run(
        "main:app",
        host=config["host"],
        port=config["port"],
        workers=config["workers"],
        log_level=config["log_level"],
        reload=config["reload"]
    )