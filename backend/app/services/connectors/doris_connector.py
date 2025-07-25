"""
Apache Doris数据仓库连接器
支持高性能查询、Stream Load和分布式计算
"""

import asyncio
import aiohttp
import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin
import numpy as np

from ...core.security_utils import decrypt_data
from ...models.data_source import DataSource


@dataclass
class DorisConfig:
    """Doris配置"""
    fe_hosts: List[str]
    be_hosts: List[str] 
    http_port: int = 8030
    query_port: int = 9030
    database: str = "default"
    username: str = "root"
    password: str = ""
    load_balance: bool = True
    timeout: int = 30


@dataclass
class DorisQueryResult:
    """Doris查询结果"""
    data: pd.DataFrame
    execution_time: float
    rows_scanned: int
    bytes_scanned: int
    is_cached: bool
    query_id: str
    fe_host: str


class DorisConnector:
    """Apache Doris连接器"""
    
    def __init__(self, config: DorisConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.current_fe_index = 0  # 当前使用的FE节点索引
        
        # HTTP会话配置
        self.timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            keepalive_timeout=60
        )
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'session'):
            await self.session.close()
    
    @classmethod
    def from_data_source(cls, data_source: DataSource) -> 'DorisConnector':
        """从数据源创建连接器"""
        
        config = DorisConfig(
            fe_hosts=data_source.doris_fe_hosts or ["localhost"],
            be_hosts=data_source.doris_be_hosts or ["localhost"], 
            http_port=data_source.doris_http_port or 8030,
            query_port=data_source.doris_query_port or 9030,
            database=data_source.doris_database or "default",
            username=data_source.doris_username or "root",
            password=decrypt_data(data_source.doris_password) if data_source.doris_password else ""
        )
        
        return cls(config)
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        
        try:
            # 测试查询
            result = await self.execute_query("SELECT 1 as test_connection")
            
            if not result.data.empty and result.data.iloc[0, 0] == 1:
                return {
                    "success": True,
                    "message": "Doris connection successful",
                    "fe_host": result.fe_host,
                    "execution_time": result.execution_time,
                    "database": self.config.database
                }
            else:
                return {
                    "success": False,
                    "error": "Unexpected test result"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    async def execute_query(
        self, 
        sql: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> DorisQueryResult:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            parameters: 查询参数
            
        Returns:
            查询结果
        """
        start_time = asyncio.get_event_loop().time()
        
        # 选择可用的FE节点
        fe_host = await self._get_available_fe_host()
        
        # 构建查询URL
        query_url = f"http://{fe_host}:{self.config.http_port}/api/query/{self.config.database}"
        
        # 准备认证
        auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        
        # 构建请求体
        request_data = {
            "sql": sql
        }
        
        if parameters:
            request_data["parameters"] = parameters
        
        try:
            async with self.session.post(
                query_url,
                json=request_data,
                auth=auth,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                result_data = await response.json()
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # 解析查询结果
            df = self._parse_query_result(result_data)
            
            return DorisQueryResult(
                data=df,
                execution_time=execution_time,
                rows_scanned=result_data.get("meta", {}).get("rows_scanned", 0),
                bytes_scanned=result_data.get("meta", {}).get("bytes_scanned", 0),
                is_cached=result_data.get("meta", {}).get("is_cached", False),
                query_id=result_data.get("meta", {}).get("query_id", ""),
                fe_host=fe_host
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Doris query failed: {e}")
            
            # 尝试切换到下一个FE节点
            await self._switch_fe_host()
            
            raise Exception(f"Query execution failed: {str(e)}")
    
    async def execute_optimized_query(
        self,
        sql: str, 
        optimization_hints: Optional[List[str]] = None
    ) -> DorisQueryResult:
        """
        执行优化查询
        
        Args:
            sql: SQL查询语句
            optimization_hints: 优化提示
            
        Returns:
            查询结果
        """
        
        # 添加Doris特定的优化提示
        optimized_sql = self._apply_optimization_hints(sql, optimization_hints or [])
        
        return await self.execute_query(optimized_sql)
    
    def _apply_optimization_hints(self, sql: str, hints: List[str]) -> str:
        """应用优化提示"""
        
        hint_comments = []
        
        # 分区裁剪提示
        if "partition_pruning" in hints:
            hint_comments.append("/*+ USE_PARTITION_PRUNE */")
        
        # 向量化执行提示  
        if "vectorization" in hints:
            hint_comments.append("/*+ VECTORIZED_ENGINE */")
        
        # 并行执行提示
        if "parallel_execution" in hints:
            hint_comments.append("/*+ PARALLEL(4) */")
        
        # 索引提示
        if "index_optimization" in hints:
            hint_comments.append("/*+ USE_INDEX */")
        
        # 将提示添加到SQL开头
        if hint_comments:
            hint_str = " ".join(hint_comments)
            return f"{hint_str} {sql}"
        
        return sql
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构"""
        
        sql = f"DESCRIBE {table_name}"
        
        try:
            result = await self.execute_query(sql)
            
            schema_info = {
                "table_name": table_name,
                "columns": [],
                "total_columns": len(result.data)
            }
            
            for _, row in result.data.iterrows():
                column_info = {
                    "name": row.get("Field", ""),
                    "type": row.get("Type", ""),
                    "nullable": row.get("Null", "") == "YES",
                    "key": row.get("Key", ""),
                    "default": row.get("Default", ""),
                    "extra": row.get("Extra", "")
                }
                schema_info["columns"].append(column_info)
            
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Failed to get table schema: {e}")
            return {"error": str(e)}
    
    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取表统计信息"""
        
        sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
        
        try:
            result = await self.execute_query(sql)
            
            if not result.data.empty:
                row = result.data.iloc[0]
                return {
                    "table_name": table_name,
                    "rows": row.get("Rows", 0),
                    "data_length": row.get("Data_length", 0),
                    "index_length": row.get("Index_length", 0),
                    "create_time": row.get("Create_time", ""),
                    "update_time": row.get("Update_time", ""),
                    "engine": row.get("Engine", "")
                }
            
            return {"error": "Table not found"}
            
        except Exception as e:
            self.logger.error(f"Failed to get table statistics: {e}")
            return {"error": str(e)}
    
    async def bulk_load_data(
        self,
        table_name: str,
        data: pd.DataFrame,
        load_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量加载数据（Stream Load）
        
        Args:
            table_name: 目标表名
            data: 要加载的数据
            load_label: 加载标签
            
        Returns:
            加载结果
        """
        
        if load_label is None:
            load_label = f"load_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 选择可用的FE节点
        fe_host = await self._get_available_fe_host()
        
        # 构建Stream Load URL
        load_url = f"http://{fe_host}:{self.config.http_port}/api/{self.config.database}/{table_name}/_stream_load"
        
        # 准备认证
        auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        
        # 转换数据为CSV格式
        csv_data = data.to_csv(index=False, header=False)
        
        # 设置加载头部
        headers = {
            "label": load_label,
            "format": "csv",
            "Content-Type": "text/plain"
        }
        
        try:
            async with self.session.put(
                load_url,
                data=csv_data,
                auth=auth,
                headers=headers
            ) as response:
                response.raise_for_status()
                result = await response.json()
            
            return {
                "success": result.get("Status") == "Success",
                "message": result.get("Message", ""),
                "load_label": load_label,
                "rows_loaded": result.get("NumberLoadedRows", 0),
                "rows_filtered": result.get("NumberFilteredRows", 0),
                "load_bytes": result.get("LoadBytes", 0),
                "load_time_ms": result.get("LoadTimeMs", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Bulk load failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "load_label": load_label
            }
    
    async def _get_available_fe_host(self) -> str:
        """获取可用的FE节点"""
        
        if not self.config.load_balance:
            return self.config.fe_hosts[0]
        
        # 简单的轮询负载均衡
        fe_host = self.config.fe_hosts[self.current_fe_index]
        self.current_fe_index = (self.current_fe_index + 1) % len(self.config.fe_hosts)
        
        return fe_host
    
    async def _switch_fe_host(self):
        """切换到下一个FE节点"""
        self.current_fe_index = (self.current_fe_index + 1) % len(self.config.fe_hosts)
        self.logger.info(f"Switched to FE host: {self.config.fe_hosts[self.current_fe_index]}")
    
    def _parse_query_result(self, result_data: Dict[str, Any]) -> pd.DataFrame:
        """解析查询结果为DataFrame"""
        
        try:
            # 检查查询是否成功
            if result_data.get("code") != 0:
                raise Exception(f"Query failed: {result_data.get('msg', 'Unknown error')}")
            
            # 获取数据和元数据
            data = result_data.get("data", [])
            meta = result_data.get("meta", [])
            
            if not data:
                # 返回空DataFrame但保持列结构
                columns = [col.get("name", f"col_{i}") for i, col in enumerate(meta)]
                return pd.DataFrame(columns=columns)
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 设置列名
            if meta:
                column_names = [col.get("name", f"col_{i}") for i, col in enumerate(meta)]
                if len(column_names) == len(df.columns):
                    df.columns = column_names
            
            # 类型转换
            if meta:
                for i, col_meta in enumerate(meta):
                    if i < len(df.columns):
                        col_name = df.columns[i]
                        col_type = col_meta.get("type", "").lower()
                        
                        try:
                            if "int" in col_type:
                                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                            elif "float" in col_type or "double" in col_type or "decimal" in col_type:
                                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                            elif "date" in col_type or "time" in col_type:
                                df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
                            elif "bool" in col_type:
                                df[col_name] = df[col_name].astype(bool)
                        except Exception as e:
                            self.logger.warning(f"Failed to convert column {col_name} to {col_type}: {e}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to parse query result: {e}")
            return pd.DataFrame()


# 工厂函数
def create_doris_connector(data_source: DataSource) -> DorisConnector:
    """创建Doris连接器"""
    return DorisConnector.from_data_source(data_source)