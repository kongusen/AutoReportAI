"""
API性能优化中间件
提供请求响应性能监控、缓存、压缩等功能
"""

import asyncio
import gzip
import json
import logging
import time
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.infrastructure.cache import cache_service

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能优化中间件"""
    
    def __init__(
        self, 
        app: ASGIApp,
        enable_compression: bool = True,
        enable_caching: bool = True,
        enable_metrics: bool = True,
        compression_threshold: int = 1024,
        cache_ttl: int = 300
    ):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_caching = enable_caching
        self.enable_metrics = enable_metrics
        self.compression_threshold = compression_threshold
        self.cache_ttl = cache_ttl
        
        # 性能指标存储
        self.metrics: Dict[str, Any] = {
            "request_count": 0,
            "total_duration": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "compression_savings": 0
        }
        
        # 缓存策略配置
        self.cacheable_methods = {"GET"}
        self.cacheable_paths = {
            "/api/v1/dashboard/stats",
            "/api/v1/dashboard/overview",
            "/api/v1/templates",
            "/api/v1/data-sources",
            "/api/v1/reports",
            "/api/v1/settings/profile"
        }
        
        # 不缓存的路径模式
        self.non_cacheable_patterns = {
            "/api/v1/auth/",
            "/api/v1/files/",
            "/ws",
            "/docs",
            "/redoc"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求和响应"""
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        try:
            # 检查缓存
            if self.enable_caching and self._is_cacheable(request):
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    self.metrics["cache_hits"] += 1
                    cached_response.headers["X-Cache-Status"] = "HIT"
                    cached_response.headers["X-Request-ID"] = request_id
                    return cached_response
                else:
                    self.metrics["cache_misses"] += 1
            
            # 处理请求
            response = await call_next(request)
            
            # 计算执行时间
            duration = (time.time() - start_time) * 1000  # 毫秒
            
            # 添加性能头
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            
            # 缓存响应
            if (self.enable_caching and 
                self._is_cacheable(request) and 
                response.status_code == 200):
                await self._cache_response(request, response)
                response.headers["X-Cache-Status"] = "MISS"
            
            # 压缩响应
            if self.enable_compression:
                response = await self._compress_response(request, response)
            
            # 更新指标
            if self.enable_metrics:
                self._update_metrics(request, response, duration)
            
            return response
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Error in performance middleware: {e}")
            
            # 记录错误指标
            if self.enable_metrics:
                self.metrics["request_count"] += 1
                self.metrics["total_duration"] += duration
            
            raise
    
    def _is_cacheable(self, request: Request) -> bool:
        """检查请求是否可缓存"""
        # 检查方法
        if request.method not in self.cacheable_methods:
            return False
        
        # 检查路径是否在不可缓存的模式中
        for pattern in self.non_cacheable_patterns:
            if str(request.url.path).startswith(pattern):
                return False
        
        # 检查是否有认证用户（用户特定数据需要用户ID作为缓存键的一部分）
        user_id = getattr(request.state, 'user_id', None)
        
        # 检查是否在可缓存路径中或者是用户特定的路径
        path = str(request.url.path)
        return (
            path in self.cacheable_paths or
            any(pattern in path for pattern in ["/dashboard", "/settings", "/history"]) or
            (user_id and any(pattern in path for pattern in ["/reports", "/templates", "/data-sources"]))
        )
    
    def _generate_cache_key(self, request: Request) -> str:
        """生成缓存键"""
        # 基础键
        base_key = f"api_cache:{request.method}:{request.url.path}"
        
        # 添加查询参数
        if request.url.query:
            base_key += f":{request.url.query}"
        
        # 添加用户ID（如果存在）
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            base_key += f":user:{user_id}"
        
        # 添加Accept头部（用于内容协商）
        accept = request.headers.get("accept", "")
        if "application/json" in accept:
            base_key += ":json"
        
        return base_key
    
    async def _get_cached_response(self, request: Request) -> Optional[Response]:
        """获取缓存响应"""
        try:
            cache_key = self._generate_cache_key(request)
            cached_data = cache_service.get(cache_key)
            
            if cached_data:
                return JSONResponse(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers=cached_data.get("headers", {})
                )
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
        
        return None
    
    async def _cache_response(self, request: Request, response: Response):
        """缓存响应"""
        try:
            # 只缓存JSON响应
            if not isinstance(response, JSONResponse):
                return
            
            cache_key = self._generate_cache_key(request)
            
            # 读取响应内容
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # 解析JSON内容
            content = json.loads(response_body.decode())
            
            # 创建缓存数据
            cache_data = {
                "content": content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "cached_at": datetime.utcnow().isoformat()
            }
            
            # 确定TTL
            ttl = self.cache_ttl
            
            # 根据路径调整TTL
            path = str(request.url.path)
            if "dashboard" in path:
                ttl = 300  # 5分钟
            elif "settings" in path:
                ttl = 1800  # 30分钟
            elif any(pattern in path for pattern in ["/templates", "/data-sources"]):
                ttl = 600   # 10分钟
            
            # 缓存数据
            cache_service.set(cache_key, cache_data, ttl)
            
            # 重新创建响应（因为body_iterator只能读取一次）
            response.body = response_body
            response.headers["X-Cache-TTL"] = str(ttl)
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
    
    async def _compress_response(self, request: Request, response: Response) -> Response:
        """压缩响应"""
        try:
            # 检查客户端是否支持gzip
            accept_encoding = request.headers.get("accept-encoding", "")
            if "gzip" not in accept_encoding.lower():
                return response
            
            # 检查响应类型
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith(("application/json", "text/")):
                return response
            
            # 获取响应内容
            if hasattr(response, 'body') and response.body:
                original_content = response.body
            elif isinstance(response, JSONResponse):
                # 对于JSONResponse，需要序列化内容
                original_content = json.dumps(response.body).encode('utf-8')
            else:
                return response
            
            # 检查内容大小
            if len(original_content) < self.compression_threshold:
                return response
            
            # 压缩内容
            compressed_content = gzip.compress(original_content)
            compression_ratio = len(compressed_content) / len(original_content)
            
            # 如果压缩效果不明显，不使用压缩
            if compression_ratio > 0.9:
                return response
            
            # 更新响应
            response.body = compressed_content
            response.headers["content-encoding"] = "gzip"
            response.headers["content-length"] = str(len(compressed_content))
            response.headers["X-Compression-Ratio"] = f"{compression_ratio:.3f}"
            
            # 更新压缩节省指标
            savings = len(original_content) - len(compressed_content)
            self.metrics["compression_savings"] += savings
            
            return response
            
        except Exception as e:
            logger.error(f"Error compressing response: {e}")
            return response
    
    def _update_metrics(self, request: Request, response: Response, duration: float):
        """更新性能指标"""
        try:
            self.metrics["request_count"] += 1
            self.metrics["total_duration"] += duration
            
            # 记录慢请求
            if duration > 1000:  # 大于1秒
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {duration:.2f}ms"
                )
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if self.metrics["request_count"] > 0:
            avg_duration = self.metrics["total_duration"] / self.metrics["request_count"]
        else:
            avg_duration = 0
        
        cache_hit_rate = 0
        if self.metrics["cache_hits"] + self.metrics["cache_misses"] > 0:
            cache_hit_rate = (
                self.metrics["cache_hits"] / 
                (self.metrics["cache_hits"] + self.metrics["cache_misses"]) * 100
            )
        
        return {
            "request_count": self.metrics["request_count"],
            "average_response_time_ms": round(avg_duration, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "compression_savings_bytes": self.metrics["compression_savings"],
            "uptime_seconds": (datetime.utcnow() - datetime.utcnow()).total_seconds()
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """请求频率限制中间件"""
    
    def __init__(self, app: ASGIApp, max_requests_per_minute: int = 60):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求限流"""
        client_ip = request.client.host if request.client else "unknown"
        current_time = datetime.utcnow()
        
        # 清理过期记录
        self._cleanup_expired_records(current_time)
        
        # 检查请求频率
        if not self._is_request_allowed(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Request rate limit exceeded. Maximum {self.max_requests} requests per minute.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # 记录请求
        self._record_request(client_ip, current_time)
        
        response = await call_next(request)
        
        # 添加限流头部
        remaining = self._get_remaining_requests(client_ip, current_time)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((current_time + timedelta(minutes=1)).timestamp()))
        
        return response
    
    def _cleanup_expired_records(self, current_time: datetime):
        """清理过期的请求记录"""
        cutoff_time = current_time - timedelta(minutes=1)
        
        for client_ip in list(self.request_counts.keys()):
            client_requests = self.request_counts[client_ip]
            client_requests["requests"] = [
                req_time for req_time in client_requests["requests"]
                if req_time > cutoff_time
            ]
            
            if not client_requests["requests"]:
                del self.request_counts[client_ip]
    
    def _is_request_allowed(self, client_ip: str, current_time: datetime) -> bool:
        """检查是否允许请求"""
        if client_ip not in self.request_counts:
            return True
        
        client_requests = self.request_counts[client_ip]
        recent_requests = [
            req_time for req_time in client_requests["requests"]
            if req_time > current_time - timedelta(minutes=1)
        ]
        
        return len(recent_requests) < self.max_requests
    
    def _record_request(self, client_ip: str, current_time: datetime):
        """记录请求"""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"requests": []}
        
        self.request_counts[client_ip]["requests"].append(current_time)
    
    def _get_remaining_requests(self, client_ip: str, current_time: datetime) -> int:
        """获取剩余请求数"""
        if client_ip not in self.request_counts:
            return self.max_requests
        
        client_requests = self.request_counts[client_ip]
        recent_requests = [
            req_time for req_time in client_requests["requests"]
            if req_time > current_time - timedelta(minutes=1)
        ]
        
        return max(0, self.max_requests - len(recent_requests))