"""
API数据源连接器
支持REST API数据源的连接和查询
"""

import asyncio
import logging
import pandas as pd
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base_connector import BaseConnector, ConnectorConfig, QueryResult


@dataclass
class APIConfig(ConnectorConfig):
    """API连接器配置"""
    api_url: str = None
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    timeout: int = 30
    auth_type: str = "none"  # none, basic, bearer, api_key
    auth_credentials: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.api_url is None:
            raise ValueError("api_url is required for APIConfig")


class APIConnector(BaseConnector):
    """API数据源连接器"""
    
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client: Optional[httpx.AsyncClient] = None
        self._connected = False
    
    async def connect(self) -> None:
        """建立API连接"""
        try:
            # 创建HTTP客户端
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers=self.config.headers or {}
            )
            
            # 测试连接
            await self.test_connection()
            
            self._connected = True
            self.logger.info(f"API connection established: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to API: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开API连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._connected = False
        self.logger.info(f"API connection closed: {self.config.name}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        try:
            if not self.client:
                await self.connect()
            
            # 发送测试请求
            response = await self.client.request(
                method=self.config.method,
                url=self.config.api_url,
                headers=self.config.headers or {},
                json=self.config.body,
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "API connection successful",
                "status_code": response.status_code,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"API connection failed: {str(e)}"
            }
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """执行API查询"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.client:
                await self.connect()
            
            # 合并查询参数
            params = parameters or {}
            
            # 发送请求
            response = await self.client.request(
                method=self.config.method,
                url=self.config.api_url,
                headers=self.config.headers or {},
                json=self.config.body,
                params=params,
            )
            response.raise_for_status()
            
            # 解析响应数据
            data = response.json()
            
            # 转换为DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # 尝试找到数据数组
                if "data" in data:
                    df = pd.DataFrame(data["data"])
                elif "items" in data:
                    df = pd.DataFrame(data["items"])
                elif "results" in data:
                    df = pd.DataFrame(data["results"])
                else:
                    df = pd.DataFrame([data])
            else:
                df = pd.DataFrame([{"value": data}])
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return QueryResult(
                data=df,
                execution_time=execution_time,
                success=True,
                metadata={
                    "status_code": response.status_code,
                    "rows_returned": len(df),
                    "columns": df.columns.tolist()
                }
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"API query failed: {e}")
            
            return QueryResult(
                data=pd.DataFrame(),
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取API字段列表"""
        try:
            if not self.client:
                await self.connect()
            
            # 获取一小部分数据来推断字段
            result = await self.execute_query("", {"limit": 1})
            
            if result.success and not result.data.empty:
                return result.data.columns.tolist()
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get API fields: {e}")
            return []
    
    async def get_tables(self) -> List[str]:
        """API通常没有表概念，返回空列表"""
        return []
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config.api_url:
            return False
        if not self.config.api_url.startswith(("http://", "https://")):
            return False
        return True
