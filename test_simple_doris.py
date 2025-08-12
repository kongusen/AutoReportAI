#!/usr/bin/env python3
"""
直接测试 Doris 连接器核心功能
"""
import asyncio
import aiohttp
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

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

class SimpleDorisConnector:
    """简化的 Doris 连接器用于测试"""
    
    def __init__(self, config: DorisConfig):
        self.config = config
        self.current_fe_index = 0
        
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
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        
        try:
            # 使用管理 API 测试连接
            fe_host = self._get_available_fe_host()
            
            # 测试基本连接和认证
            url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
            params = {'path': '/'}
            auth = aiohttp.BasicAuth(self.config.username, self.config.password)
            
            async with self.session.get(url, params=params, auth=auth) as response:
                response.raise_for_status()
                result = await response.json()
            
            if result.get("code") == 0 and result.get("msg") == "success":
                return {
                    "success": True,
                    "message": "Doris connection successful",
                    "fe_host": fe_host,
                    "database": self.config.database,
                    "version_info": "Doris connection validated via management API"
                }
            else:
                return {
                    "success": False,
                    "error": f"Connection test failed: {result.get('msg', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    async def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            fe_host = self._get_available_fe_host()
            url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
            params = {'path': '/dbs'}
            auth = aiohttp.BasicAuth(self.config.username, self.config.password)
            
            async with self.session.get(url, params=params, auth=auth) as response:
                response.raise_for_status()
                result = await response.json()
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "databases": result.get("data", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.get('msg', 'Failed to get database info')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_tables_info(self, database_id: str) -> Dict[str, Any]:
        """获取表信息"""
        try:
            fe_host = self._get_available_fe_host()
            url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
            params = {'path': f'/dbs/{database_id}'}
            auth = aiohttp.BasicAuth(self.config.username, self.config.password)
            
            async with self.session.get(url, params=params, auth=auth) as response:
                response.raise_for_status()
                result = await response.json()
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "tables": result.get("data", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.get('msg', 'Failed to get tables info')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_available_fe_host(self) -> str:
        """获取可用的FE节点"""
        if not self.config.load_balance:
            return self.config.fe_hosts[0]
        
        # 简单的轮询负载均衡
        fe_host = self.config.fe_hosts[self.current_fe_index]
        self.current_fe_index = (self.current_fe_index + 1) % len(self.config.fe_hosts)
        
        return fe_host

async def test_doris_connector():
    print("测试简化的 Doris 连接器...")
    
    config = DorisConfig(
        fe_hosts=["192.168.61.30"],
        be_hosts=["192.168.61.30"],
        http_port=8030,
        query_port=9030,
        database="yjg",
        username="root",
        password="yjg@123456"
    )
    
    async with SimpleDorisConnector(config) as connector:
        print("\n1. 测试连接...")
        result = await connector.test_connection()
        print(f"连接结果: {result}")
        
        if result.get("success"):
            print("\n2. 获取数据库列表...")
            db_result = await connector.get_database_info()
            print(f"数据库信息: {db_result}")
            
            if db_result.get("success"):
                # 查找 yjg 数据库的 ID
                databases = db_result.get("databases", [])
                yjg_db_id = None
                
                print("所有数据库:")
                for db in databases:
                    if len(db) > 1:
                        print(f"  ID: {db[0]}, 名称: {db[1]}")
                        if db[1] == "yjg":
                            yjg_db_id = db[0]
                
                if yjg_db_id:
                    print(f"\n3. 获取 yjg 数据库 (ID: {yjg_db_id}) 的表列表...")
                    tables_result = await connector.get_tables_info(yjg_db_id)
                    print(f"表信息: {tables_result}")
                    
                    if tables_result.get("success"):
                        tables = tables_result.get("tables", [])
                        print("前10个表:")
                        for i, table in enumerate(tables[:10]):
                            if len(table) > 1:
                                print(f"  {i+1}. 表ID: {table[0]}, 表名: {table[1]}")

if __name__ == "__main__":
    asyncio.run(test_doris_connector())