"""
异步MCP工具客户端
支持连接池、批量调用和错误重试
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from contextlib import asynccontextmanager

from ..core.config import settings


class MCPToolType(Enum):
    """MCP工具类型"""
    DATA_ANALYSIS = "data_analysis"
    CHART_GENERATION = "chart_generation"
    TEXT_SUMMARY = "text_summary"
    STATISTICS = "statistics"


@dataclass
class MCPRequest:
    """MCP请求"""
    tool_type: MCPToolType
    endpoint: str
    payload: Dict[str, Any]
    priority: int = 1
    timeout: float = 30.0
    retry_count: int = 3


@dataclass
class MCPResponse:
    """MCP响应"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False


class AsyncMCPClient:
    """异步MCP客户端"""
    
    def __init__(self, max_connections: int = 20, timeout: float = 30.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # 连接池配置
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=10,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        # 创建会话
        self.session = None
        self._session_lock = asyncio.Lock()
        
        # 请求队列和批处理
        self.request_queue = asyncio.Queue()
        self.batch_size = 5
        self.batch_timeout = 0.5  # 500ms批处理超时
        
        # 缓存
        self.response_cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 启动批处理任务
        self._batch_task = None
        
    async def __aenter__(self):
        await self._ensure_session()
        self._batch_task = asyncio.create_task(self._batch_processor())
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
                
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """确保会话已创建"""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self.session = aiohttp.ClientSession(
                    connector=self.connector,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )
    
    async def call_tool(
        self, 
        tool_type: MCPToolType,
        endpoint: str,
        payload: Dict[str, Any],
        priority: int = 1,
        use_cache: bool = True
    ) -> MCPResponse:
        """
        调用MCP工具
        
        Args:
            tool_type: 工具类型
            endpoint: API端点
            payload: 请求数据
            priority: 优先级(数字越大优先级越高)
            use_cache: 是否使用缓存
            
        Returns:
            MCP响应
        """
        # 检查缓存
        if use_cache:
            cache_key = self._generate_cache_key(endpoint, payload)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                cached_response.cached = True
                return cached_response
        
        # 创建请求
        request = MCPRequest(
            tool_type=tool_type,
            endpoint=endpoint,
            payload=payload,
            priority=priority
        )
        
        # 创建响应Future
        response_future = asyncio.Future()
        
        # 将请求加入队列
        await self.request_queue.put((request, response_future))
        
        # 等待响应
        response = await response_future
        
        # 缓存成功的响应
        if use_cache and response.success:
            cache_key = self._generate_cache_key(endpoint, payload)
            self._cache_response(cache_key, response)
        
        return response
    
    async def call_tools_batch(
        self, 
        requests: List[MCPRequest]
    ) -> List[MCPResponse]:
        """
        批量调用MCP工具
        
        Args:
            requests: 请求列表
            
        Returns:
            响应列表
        """
        # 创建响应Future列表
        response_futures = []
        
        for request in requests:
            response_future = asyncio.Future()
            response_futures.append(response_future)
            await self.request_queue.put((request, response_future))
        
        # 等待所有响应
        responses = await asyncio.gather(*response_futures, return_exceptions=True)
        
        # 处理异常
        processed_responses = []
        for response in responses:
            if isinstance(response, Exception):
                processed_responses.append(MCPResponse(
                    success=False,
                    data=None,
                    error=str(response)
                ))
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def _batch_processor(self):
        """批处理任务处理器"""
        while True:
            try:
                batch = []
                futures = []
                
                # 收集批次请求
                try:
                    # 等待第一个请求
                    request, future = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=1.0
                    )
                    batch.append(request)
                    futures.append(future)
                    
                    # 收集更多请求直到批次大小或超时
                    while len(batch) < self.batch_size:
                        try:
                            request, future = await asyncio.wait_for(
                                self.request_queue.get(),
                                timeout=self.batch_timeout
                            )
                            batch.append(request)
                            futures.append(future)
                        except asyncio.TimeoutError:
                            break
                            
                except asyncio.TimeoutError:
                    # 没有请求，继续等待
                    continue
                
                # 处理批次
                if batch:
                    await self._process_batch(batch, futures)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Batch processing error: {e}")
    
    async def _process_batch(
        self, 
        batch: List[MCPRequest], 
        futures: List[asyncio.Future]
    ):
        """处理请求批次"""
        
        # 按优先级排序
        sorted_items = sorted(
            zip(batch, futures), 
            key=lambda x: x[0].priority, 
            reverse=True
        )
        batch, futures = zip(*sorted_items)
        
        # 按工具类型分组
        grouped_requests = self._group_requests_by_type(batch, futures)
        
        # 并发处理每个组
        tasks = []
        for tool_type, group_items in grouped_requests.items():
            task = asyncio.create_task(
                self._process_tool_group(tool_type, group_items)
            )
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _group_requests_by_type(
        self, 
        batch: List[MCPRequest], 
        futures: List[asyncio.Future]
    ) -> Dict[MCPToolType, List[tuple]]:
        """按工具类型分组请求"""
        
        groups = {}
        for request, future in zip(batch, futures):
            tool_type = request.tool_type
            if tool_type not in groups:
                groups[tool_type] = []
            groups[tool_type].append((request, future))
        
        return groups
    
    async def _process_tool_group(
        self, 
        tool_type: MCPToolType, 
        group_items: List[tuple]
    ):
        """处理同类型工具组"""
        
        # 对于某些工具类型，可以进行批量调用优化
        if tool_type == MCPToolType.DATA_ANALYSIS and len(group_items) > 1:
            await self._process_data_analysis_batch(group_items)
        else:
            # 并发处理单个请求
            tasks = [
                self._process_single_request(request, future)
                for request, future in group_items
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_data_analysis_batch(self, group_items: List[tuple]):
        """批量处理数据分析请求"""
        
        # 合并数据分析请求
        combined_payload = {
            "batch_requests": []
        }
        
        for request, _ in group_items:
            combined_payload["batch_requests"].append({
                "endpoint": request.endpoint,
                "payload": request.payload
            })
        
        # 发送批量请求
        try:
            await self._ensure_session()
            base_url = settings.SERVICE_URLS.get("ai_service", "")
            url = f"{base_url}/tools/batch-analyze"
            
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.post(url, json=combined_payload) as response:
                response.raise_for_status()
                batch_result = await response.json()
                
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # 分发结果给各个Future
            batch_responses = batch_result.get("results", [])
            for (request, future), result in zip(group_items, batch_responses):
                mcp_response = MCPResponse(
                    success=result.get("success", False),
                    data=result.get("data"),
                    error=result.get("error"),
                    execution_time=execution_time / len(group_items)
                )
                future.set_result(mcp_response)
            
        except Exception as e:
            # 发生错误时，所有请求都返回错误
            for request, future in group_items:
                mcp_response = MCPResponse(
                    success=False,
                    data=None,
                    error=str(e)
                )
                future.set_result(mcp_response)
    
    async def _process_single_request(
        self, 
        request: MCPRequest, 
        future: asyncio.Future
    ):
        """处理单个请求"""
        
        start_time = asyncio.get_event_loop().time()
        
        for attempt in range(request.retry_count):
            try:
                await self._ensure_session()
                
                # 构建URL
                base_url = settings.SERVICE_URLS.get("ai_service", "")
                url = f"{base_url}{request.endpoint}"
                
                # 发送请求
                async with self.session.post(url, json=request.payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                mcp_response = MCPResponse(
                    success=True,
                    data=data,
                    execution_time=execution_time
                )
                
                future.set_result(mcp_response)
                return
                
            except Exception as e:
                if attempt == request.retry_count - 1:
                    # 最后一次尝试失败
                    execution_time = asyncio.get_event_loop().time() - start_time
                    mcp_response = MCPResponse(
                        success=False,
                        data=None,
                        error=str(e),
                        execution_time=execution_time
                    )
                    future.set_result(mcp_response)
                else:
                    # 重试前等待
                    await asyncio.sleep(2 ** attempt)  # 指数退避
    
    def _generate_cache_key(self, endpoint: str, payload: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
        return f"mcp_cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[MCPResponse]:
        """获取缓存响应"""
        if cache_key in self.response_cache:
            cached_data, timestamp = self.response_cache[cache_key]
            if asyncio.get_event_loop().time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # 缓存过期，删除
                del self.response_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: MCPResponse):
        """缓存响应"""
        # 只缓存成功的响应
        if response.success:
            timestamp = asyncio.get_event_loop().time()
            self.response_cache[cache_key] = (response, timestamp)
            
            # 限制缓存大小
            if len(self.response_cache) > 1000:
                # 删除最旧的缓存项
                oldest_key = min(
                    self.response_cache.keys(),
                    key=lambda k: self.response_cache[k][1]
                )
                del self.response_cache[oldest_key]


# 创建全局异步客户端实例
@asynccontextmanager
async def get_async_mcp_client():
    """获取异步MCP客户端上下文管理器"""
    async with AsyncMCPClient() as client:
        yield client