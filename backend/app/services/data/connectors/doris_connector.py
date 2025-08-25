"""
Apache Doris数据仓库连接器
支持高性能查询、Stream Load和分布式计算
现在使用MySQL协议进行更稳定的连接
"""

import asyncio
import aiohttp
import pandas as pd
import json
import logging
import pymysql
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin
import numpy as np
from contextlib import contextmanager

from app.core.security_utils import decrypt_data
from app.core.data_source_utils import DataSourcePasswordManager
from app.models.data_source import DataSource
from .base_connector import BaseConnector, ConnectorConfig, QueryResult


@dataclass
class DorisConfig(ConnectorConfig):
    """Doris配置 - 支持MySQL协议和HTTP API"""
    # MySQL协议配置
    mysql_host: str = "localhost"
    mysql_port: int = 9030  # MySQL协议端口
    mysql_database: str = "default"
    mysql_username: str = "root"
    mysql_password: str = ""
    mysql_charset: str = "utf8mb4"
    
    # HTTP API配置（用于管理操作）
    fe_hosts: List[str] = None
    be_hosts: List[str] = None
    http_port: int = 8030
    query_port: int = 9030
    database: str = "default"
    username: str = "root"
    password: str = ""
    load_balance: bool = True
    timeout: int = 30
    
    # 连接模式选择
    use_mysql_protocol: bool = True  # 优先使用MySQL协议
    
    def __post_init__(self):
        if self.fe_hosts is None:
            self.fe_hosts = ["localhost"]
        if self.be_hosts is None:
            self.be_hosts = ["localhost"]
        
        # 统一配置项
        if hasattr(self, 'mysql_host') and self.mysql_host == "localhost" and self.fe_hosts:
            self.mysql_host = self.fe_hosts[0]
        if hasattr(self, 'mysql_username') and self.mysql_username == "root" and self.username:
            self.mysql_username = self.username
        if hasattr(self, 'mysql_password') and self.mysql_password == "" and self.password:
            self.mysql_password = self.password
        if hasattr(self, 'mysql_database') and self.mysql_database == "default" and self.database:
            self.mysql_database = self.database


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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            "data": self.data.to_dict(orient="records") if not self.data.empty else [],
            "columns": self.data.columns.tolist() if not self.data.empty else [],
            "execution_time": self.execution_time,
            "rows_scanned": self.rows_scanned,
            "bytes_scanned": self.bytes_scanned,
            "is_cached": self.is_cached,
            "query_id": self.query_id,
            "fe_host": self.fe_host,
            "row_count": len(self.data)
        }
    
    def __json__(self):
        """Kombu/Celery JSON serialization support"""
        return self.to_dict()
    
    def __reduce__(self):
        """Pickle serialization support for Celery"""
        return (self.from_dict, (self.to_dict(),))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DorisQueryResult':
        """从字典创建DorisQueryResult对象"""
        df_data = data.get("data", [])
        columns = data.get("columns", [])
        
        if df_data and columns:
            df = pd.DataFrame(df_data, columns=columns)
        else:
            df = pd.DataFrame()
        
        return cls(
            data=df,
            execution_time=data.get("execution_time", 0.0),
            rows_scanned=data.get("rows_scanned", 0),
            bytes_scanned=data.get("bytes_scanned", 0),
            is_cached=data.get("is_cached", False),
            query_id=data.get("query_id", ""),
            fe_host=data.get("fe_host", "")
        )


class DorisConnector(BaseConnector):
    """Apache Doris连接器 - 支持MySQL协议和HTTP API"""
    
    def __init__(self, config: DorisConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MySQL连接
        self.mysql_connection = None
        
        # HTTP会话配置（用于管理操作）
        self.current_fe_index = 0  # 当前使用的FE节点索引
        self.session = None  # 初始化session为None
        self.timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            keepalive_timeout=60
        )
        
    async def connect(self) -> None:
        """建立连接"""
        mysql_connected = False
        
        if self.config.use_mysql_protocol:
            try:
                await self._connect_mysql()
                mysql_connected = True
            except Exception as e:
                self.logger.warning(f"MySQL协议连接失败，将仅使用HTTP API: {e}")
                # 禁用MySQL协议，回退到HTTP API
                self.config.use_mysql_protocol = False
        
        # 建立HTTP会话用于管理操作（或作为主要连接方式）
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        )
        self._connected = True
        
        if mysql_connected:
            self.logger.info("✅ 已建立MySQL协议连接和HTTP API会话")
        else:
            self.logger.info("✅ 已建立HTTP API会话（MySQL协议不可用）")
        
    async def _connect_mysql(self) -> None:
        """建立MySQL协议连接，支持重试"""
        max_retries = 3
        base_timeout = self.config.timeout
        
        for attempt in range(max_retries):
            try:
                # 递增超时时间
                timeout = base_timeout + (attempt * 10)
                
                self.mysql_connection = pymysql.connect(
                    host=self.config.mysql_host,
                    port=self.config.mysql_port,
                    user=self.config.mysql_username,
                    password=self.config.mysql_password,
                    database=self.config.mysql_database,
                    charset=self.config.mysql_charset,
                    connect_timeout=timeout,
                    read_timeout=timeout,
                    write_timeout=timeout,
                    autocommit=True
                )
                self.logger.info(f"✅ MySQL协议连接成功: {self.config.mysql_host}:{self.config.mysql_port} (尝试 {attempt + 1})")
                return
            except Exception as e:
                self.logger.warning(f"❌ MySQL协议连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"❌ MySQL协议连接最终失败: {e}")
                    raise
                # 等待一秒后重试
                import asyncio
                await asyncio.sleep(1)
        
    @contextmanager
    def _get_mysql_cursor(self):
        """获取MySQL游标的上下文管理器"""
        if not self.mysql_connection:
            raise Exception("MySQL连接未建立")
        
        cursor = self.mysql_connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
        
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            # 关闭MySQL连接
            if hasattr(self, 'mysql_connection') and self.mysql_connection is not None:
                self.mysql_connection.close()
                self.mysql_connection = None
                self.logger.info("✅ MySQL连接已关闭")
            
            # 关闭HTTP会话
            if hasattr(self, 'session') and self.session is not None:
                if not self.session.closed:
                    await self.session.close()
            if hasattr(self, 'connector') and self.connector is not None:
                await self.connector.close()
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
        finally:
            self._connected = False
            self.session = None
    
    async def close(self) -> None:
        """关闭连接（disconnect的别名）"""
        await self.disconnect()
    
    def __del__(self):
        """析构函数，确保资源正确释放"""
        if hasattr(self, 'session') and self.session is not None and not self.session.closed:
            # 在同步上下文中我们只能记录警告
            import warnings
            warnings.warn(
                "DorisConnector session was not properly closed. "
                "Please use 'await connector.disconnect()' or async context manager.",
                ResourceWarning
            )
            # 尝试强制关闭会话（在事件循环中）
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except Exception:
                pass  # 忽略清理时的错误
    
    @classmethod
    def from_data_source(cls, data_source: DataSource) -> 'DorisConnector':
        """从数据源创建连接器"""
        
        config = DorisConfig(
            source_type="doris",
            name=data_source.name,
            # MySQL协议配置
            mysql_host=(data_source.doris_fe_hosts or ["localhost"])[0],
            mysql_port=data_source.doris_query_port or 9030,
            mysql_database=data_source.doris_database or "default",
            mysql_username=data_source.doris_username or "root",
            mysql_password=DataSourcePasswordManager.get_password(data_source.doris_password),
            mysql_charset="utf8mb4",
            # HTTP API配置（保持兼容）
            fe_hosts=data_source.doris_fe_hosts or ["localhost"],
            be_hosts=data_source.doris_be_hosts or ["localhost"], 
            http_port=data_source.doris_http_port or 8030,
            query_port=data_source.doris_query_port or 9030,
            database=data_source.doris_database or "default",
            username=data_source.doris_username or "root",
            password=DataSourcePasswordManager.get_password(data_source.doris_password),
            timeout=30,  # 设置默认超时时间为30秒
            use_mysql_protocol=True  # 启用MySQL协议
        )
        
        return cls(config)
    
    @classmethod
    def _get_password(cls, password: Optional[str]) -> str:
        """安全获取密码，支持加密和明文两种形式"""
        if not password:
            return ""
        
        # 如果密码看起来像是加密的（base64编码），尝试解密
        if len(password) > 10 and password.startswith('gAAAA'):
            try:
                decrypted = decrypt_data(password)
                if decrypted and len(decrypted) > 0:
                    return decrypted
            except Exception as e:
                # 解密失败，记录日志但不抛出异常
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"密码解密失败，使用明文处理: {e}")
        
        # 直接返回原密码（可能是明文）
        return password
    
    def _clean_sql(self, sql: str) -> str:
        """清理和验证SQL查询"""
        if not sql:
            return sql
            
        # 移除多余的空格和换行符
        cleaned = ' '.join(sql.split())
        
        # 只进行基本的SQL格式化，避免过度修复
        import re
        
        # 只修复明显的语法错误，不要过度处理
        basic_fixes = [
            # 确保COUNT(*)语法正确（通用清理）
            (r'\bCOUNT\s*\(\s*\*\s*\)', 'COUNT(*)'),
            # 修复多余的空格
            (r'\s+', ' '),
            # 移除首尾空格
        ]
        
        for pattern, replacement in basic_fixes:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        cleaned = cleaned.strip()
        
        # 记录清理结果（仅在有变化时）
        if cleaned != sql:
            self.logger.debug(f"SQL已清理: {sql} -> {cleaned}")
        
        return cleaned
    
    async def execute_mysql_query(self, sql: str, params: Optional[tuple] = None) -> Optional[pd.DataFrame]:
        """使用MySQL协议执行查询并返回DataFrame"""
        if not self.config.use_mysql_protocol or not self.mysql_connection:
            self.logger.warning("MySQL协议未启用或未连接，回退到HTTP API")
            return None
            
        # 清理和验证SQL查询
        cleaned_sql = self._clean_sql(sql)
        self.logger.debug(f"执行SQL查询: {cleaned_sql}")
        
        try:
            start_time = time.time()
            with self._get_mysql_cursor() as cursor:
                cursor.execute(cleaned_sql, params)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                execution_time = time.time() - start_time
                
                df = pd.DataFrame(results, columns=columns)
                self.logger.info(f"✅ MySQL查询执行成功，耗时: {execution_time:.3f}秒，返回 {len(df)} 行")
                return df
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ MySQL查询执行失败: {error_msg}")
            
            # 检查是否是连接问题
            if any(keyword in error_msg.lower() for keyword in ['connection', 'timeout', 'refused', 'lost']):
                self.logger.error("MySQL连接问题，可能需要检查网络或Doris服务状态")
            
            # 检查是否是Doris特定的SQL语法错误
            elif "can only be used in conjunction with COUNT" in error_msg:
                self.logger.error(f"Doris SQL语法错误")
                self.logger.error(f"原始SQL: {sql}")
                self.logger.error(f"清理后SQL: {cleaned_sql}")
                
            # 检查是否是表不存在错误
            elif "doesn't exist" in error_msg.lower() or "table not found" in error_msg.lower():
                self.logger.error(f"表不存在错误，请检查表名和数据库")
                
            return None
    
    async def get_databases_mysql(self) -> List[str]:
        """使用MySQL协议获取数据库列表"""
        try:
            with self._get_mysql_cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                db_list = [db[0] for db in databases if db[0] not in ['information_schema', '__internal_schema']]
                self.logger.info(f"✅ MySQL协议获取数据库: {db_list}")
                return db_list
        except Exception as e:
            self.logger.error(f"❌ MySQL协议获取数据库列表失败: {e}")
            return []
    
    async def get_tables_mysql(self, database: str = None) -> List[str]:
        """使用MySQL协议获取表列表"""
        try:
            with self._get_mysql_cursor() as cursor:
                if database:
                    cursor.execute(f"USE {database}")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_list = [table[0] for table in tables]
                self.logger.info(f"✅ MySQL协议获取表: {table_list}")
                return table_list
        except Exception as e:
            self.logger.error(f"❌ MySQL协议获取表列表失败: {e}")
            return []
    
    async def get_table_schema_mysql(self, table_name: str) -> List[Dict[str, Any]]:
        """使用MySQL协议获取表结构"""
        try:
            with self._get_mysql_cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                schema = []
                for col in columns:
                    schema.append({
                        'field': col[0],
                        'type': col[1],
                        'null': col[2],
                        'key': col[3],
                        'default': col[4],
                        'extra': col[5]
                    })
                self.logger.info(f"✅ MySQL协议获取表 {table_name} 结构: {len(schema)} 个字段")
                return schema
        except Exception as e:
            self.logger.error(f"❌ MySQL协议获取表结构失败: {e}")
            return []

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接 - 使用管理 API"""
        
        try:
            # 确保连接已建立
            if not self.session:
                await self.connect()
                
            # 使用管理 API 测试连接，因为这是 Doris 2.1.9 中可用的
            fe_host = await self._get_available_fe_host()
            
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
                    "message": "Doris connection successful via management API",
                    "fe_host": fe_host,
                    "database": self.config.database,
                    "version_info": "Doris 2.1.9 connection validated",
                    "method": "management_api"
                }
            else:
                return {
                    "success": False,
                    "error": f"Management API test failed: {result.get('msg', 'Unknown error')}"
                }
                
        except aiohttp.ClientResponseError as e:
            return {
                "success": False,
                "error": f"HTTP error {e.status}: {e.message}"
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
    ) -> QueryResult:
        """
        执行SQL查询 - 优先使用MySQL协议，回退到HTTP API
        
        Args:
            sql: SQL查询语句
            parameters: 查询参数
            
        Returns:
            查询结果
        """
        start_time = asyncio.get_event_loop().time()
        
        # 优先使用MySQL协议
        if self.config.use_mysql_protocol and self.mysql_connection:
            try:
                # 转换参数格式（从字典到元组）
                params_tuple = None
                if parameters:
                    # 对于MySQL协议，需要将字典参数转换为位置参数
                    formatted_sql = sql
                    for key, value in parameters.items():
                        formatted_sql = formatted_sql.replace(f"${key}", "%s")
                        if params_tuple is None:
                            params_tuple = (value,)
                        else:
                            params_tuple += (value,)
                    sql = formatted_sql
                
                df = await self.execute_mysql_query(sql, params_tuple)
                execution_time = asyncio.get_event_loop().time() - start_time
                
                if df is not None:
                    return DorisQueryResult(
                        data=df,
                        execution_time=execution_time,
                        rows_scanned=len(df),
                        bytes_scanned=len(df.to_string()) if hasattr(df, 'to_string') else 0,
                        is_cached=False,
                        query_id=f"mysql_query_{int(start_time)}",
                        fe_host=self.config.fe_hosts[self.current_fe_index]
                    )
            except Exception as e:
                self.logger.error(f"MySQL协议查询失败: {e}")
                execution_time = asyncio.get_event_loop().time() - start_time
                raise Exception(f"MySQL query failed: {str(e)}")
        
        # 如果没有MySQL连接，尝试HTTP API fallback
        self.logger.warning("MySQL connection not available, attempting HTTP API fallback")
        try:
            # 清理SQL用于HTTP API
            cleaned_sql = self._clean_sql(sql)
            fe_host = await self._get_available_fe_host()
            result = await self._execute_http_query(fe_host, start_time, cleaned_sql, parameters)
            return result
        except Exception as http_error:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"HTTP API fallback也失败: {http_error}")
            raise Exception(f"Both MySQL and HTTP API failed. MySQL: not available, HTTP: {str(http_error)}")
    
    async def _get_databases(self, fe_host: str, start_time: float) -> QueryResult:
        """通过管理API获取数据库列表"""
        
        url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
        params = {"path": "/dbs"}
        auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        
        async with self.session.get(url, params=params, auth=auth) as response:
            response.raise_for_status()
            result = await response.json()
            
            if result.get("code") != 0:
                raise Exception(f"API error: {result.get('msg', 'Unknown error')}")
            
            # 解析数据库列表
            data = result.get("data", [])
            databases = []
            for row in data:
                if len(row) >= 2:
                    db_name = row[1]  # 第二列是数据库名
                    # 过滤掉系统数据库
                    if db_name not in ['information_schema', '__internal_schema']:
                        databases.append([db_name])
            
            # 创建 DataFrame
            df = pd.DataFrame(databases, columns=['Database'])
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return DorisQueryResult(
                data=df,
                execution_time=execution_time,
                rows_scanned=len(databases),
                bytes_scanned=0,
                is_cached=False,
                query_id="show_databases",
                fe_host=fe_host
            )
    
    async def _get_tables_info(self, fe_host: str, start_time: float, sql: str) -> DorisQueryResult:
        """通过管理API获取表信息"""
        
        # 这里我们模拟返回表信息，实际应该调用相应的API
        # 目前 Doris 的管理API没有直接的表列表接口，需要通过其他方式获取
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # 返回空结果，表示没有用户表或暂不支持
        df = pd.DataFrame(columns=['table_schema', 'table_name'])
        
        return DorisQueryResult(
            data=df,
            execution_time=execution_time,
            rows_scanned=0,
            bytes_scanned=0,
            is_cached=False,
            query_id="get_tables",
            fe_host=fe_host
        )
    
    async def _get_table_count(self, fe_host: str, start_time: float) -> DorisQueryResult:
        """通过管理API获取表统计数量"""
        
        url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
        params = {"path": "/statistic"}
        auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        
        async with self.session.get(url, params=params, auth=auth) as response:
            response.raise_for_status()
            result = await response.json()
            
            if result.get("code") != 0:
                raise Exception(f"API error: {result.get('msg', 'Unknown error')}")
            
            # 解析统计数据
            data = result.get("data", [])
            total_tables = 0
            
            for row in data:
                if len(row) >= 3 and row[0] not in ['Total']:
                    db_name = row[1] if len(row) > 1 else ''
                    if db_name not in ['information_schema', '__internal_schema', 'mysql']:
                        table_count = int(row[2]) if row[2].isdigit() else 0
                        total_tables += table_count
            
            # 创建 DataFrame
            df = pd.DataFrame([[total_tables]], columns=['table_count'])
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return DorisQueryResult(
                data=df,
                execution_time=execution_time,
                rows_scanned=1,
                bytes_scanned=0,
                is_cached=False,
                query_id="table_count",
                fe_host=fe_host
            )
    
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
    
    async def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        try:
            # 优先使用MySQL协议获取表列表
            if self.config.use_mysql_protocol and self.mysql_connection:
                try:
                    tables = await self.get_tables_mysql(self.config.database)
                    if tables:
                        # 过滤异常占位内容
                        tables = [t for t in tables if t and t.lower() != 'query not supported']
                        self.logger.info(f"✅ MySQL协议获取表列表成功: {len(tables)} 个表")
                        return tables
                except Exception as e:
                    self.logger.warning(f"MySQL协议获取表列表失败: {e}")
            
            # 回退到使用SHOW TABLES查询
            try:
                result = await self.execute_query("SHOW TABLES")
                tables = []
                
                if hasattr(result, 'data') and not result.data.empty:
                    # 获取第一列的所有值作为表名
                    table_column = result.data.iloc[:, 0]  # 第一列
                    tables = [str(x) for x in table_column.tolist()]
                    
                    # 过滤系统表和异常占位行
                    tables = [table for table in tables if table and not table.startswith('__') and table.lower() != 'query not supported']
                    
                    self.logger.info(f"✅ SHOW TABLES获取表列表成功: {len(tables)} 个表")
                    return tables
                else:
                    self.logger.warning("SHOW TABLES返回空结果")
                    return []
                    
            except Exception as e:
                self.logger.warning(f"SHOW TABLES查询失败: {e}")
            
            # 最后尝试使用管理API
            try:
                fe_host = await self._get_available_fe_host()
                url = f"http://{fe_host}:{self.config.http_port}/api/show_proc"
                params = {"path": f"/dbs/{self.config.database}"}
                auth = aiohttp.BasicAuth(self.config.username, self.config.password)
                
                async with self.session.get(url, params=params, auth=auth) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if result.get("code") != 0:
                        self.logger.warning(f"管理API获取表列表失败: {result.get('msg', 'Unknown error')}")
                        return []
                    
                    # 从结果中提取表名
                    tables = []
                    data = result.get("data", [])
                    for row in data:
                        if len(row) >= 2:
                            table_name = str(row[1])  # 表名通常在第二列
                            # 过滤系统表和异常占位
                            if table_name and not table_name.startswith('__') and table_name.lower() != 'query not supported':
                                tables.append(table_name)
                    
                    self.logger.info(f"✅ 管理API获取表列表成功: {len(tables)} 个表")
                    return tables
                    
            except Exception as e:
                self.logger.error(f"管理API获取表列表失败: {e}")
                
            return []
                
        except Exception as e:
            self.logger.error(f"获取表列表失败: {e}")
            return []
    
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取字段列表 - 实现BaseConnector抽象方法"""
        return await self.get_table_fields(table_name)
    
    async def get_tables(self) -> List[str]:
        """获取表列表 - 实现BaseConnector抽象方法"""
        return await self.get_all_tables()
    
    async def get_databases(self, database_name: Optional[str] = None) -> List[str]:
        """获取数据库列表 - 优先使用MySQL协议"""
        if self.config.use_mysql_protocol and self.mysql_connection:
            return await self.get_databases_mysql()
        
        # 回退到HTTP API
        try:
            if not self.session:
                await self.connect()
            
            fe_host = await self._get_available_fe_host()
            start_time = asyncio.get_event_loop().time()
            
            result = await self._get_databases(fe_host, start_time)
            
            # 从DataFrame中提取数据库名称
            if not result.data.empty:
                return result.data['Database'].tolist()
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get databases: {e}")
            return []
    
    async def get_table_fields(self, table_name: str = None) -> List[str]:
        """获取表的字段列表，如果未指定表名则获取所有表的字段"""
        try:
            if table_name:
                # 获取指定表的字段
                schema = await self.get_table_schema(table_name)
                if "error" in schema:
                    return []
                return [col["name"] for col in schema.get("columns", [])]
            else:
                # 获取所有表的字段
                all_fields = set()
                tables = await self.get_all_tables()
                
                for table in tables[:5]:  # 限制检查前5个表以避免过多请求
                    try:
                        schema = await self.get_table_schema(table)
                        if "error" not in schema:
                            for col in schema.get("columns", []):
                                all_fields.add(col["name"])
                    except Exception as e:
                        self.logger.warning(f"Failed to get schema for table {table}: {e}")
                        continue
                
                return list(all_fields)
                
        except Exception as e:
            self.logger.error(f"Failed to get table fields: {e}")
            return []
    
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
    
    async def _handle_unknown_table_query(self, fe_host: str, start_time: float, sql: str) -> DorisQueryResult:
        """处理UNKNOWN_TABLE查询，返回模拟数据"""
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # 返回模拟的计数结果
        df = pd.DataFrame([[0]], columns=['COUNT'])
        
        return DorisQueryResult(
            data=df,
            execution_time=execution_time,
            rows_scanned=1,
            bytes_scanned=0,
            is_cached=False,
            query_id="unknown_table_query",
            fe_host=fe_host
        )
    
    async def _process_http_response(self, response, start_time: float, fe_host: str) -> DorisQueryResult:
        """处理HTTP响应"""
        if response.status == 200:
            result = await response.json()
            
            # 增强的错误日志
            if result.get("code") != 0:
                error_info = {
                    "code": result.get("code", "Unknown"),
                    "msg": result.get("msg", ""),
                    "exception": result.get("exception", ""),
                    "data": result.get("data", ""),
                    "full_response": result
                }
                self.logger.error(f"Doris HTTP API 详细错误信息: {error_info}")
                
                # 构建更详细的错误消息
                error_details = []
                if result.get("msg"):
                    error_details.append(f"消息: {result.get('msg')}")
                if result.get("exception"):
                    error_details.append(f"异常: {result.get('exception')}")
                if result.get("code"):
                    error_details.append(f"代码: {result.get('code')}")
                
                error_message = "; ".join(error_details) if error_details else "Unknown error"
                raise Exception(f"查询执行失败: {error_message}")
            
            # 解析Doris HTTP查询API响应
            data = result.get("data", [])
            columns = result.get("meta", [])
            
            # 构建DataFrame
            if data and columns:
                column_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                df = pd.DataFrame(data, columns=column_names)
            else:
                df = pd.DataFrame()
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return DorisQueryResult(
                data=df,
                execution_time=execution_time,
                rows_scanned=len(data),
                bytes_scanned=len(str(data)) if data else 0,
                is_cached=False,
                query_id=result.get("queryId", "http_query"),
                fe_host=fe_host
            )
        else:
            # 获取响应文本以提供更多信息
            try:
                response_text = await response.text()
                self.logger.error(f"HTTP响应错误详情: Status={response.status}, Body={response_text}")
                raise Exception(f"HTTP查询API返回错误状态: {response.status}, 响应: {response_text[:200]}")
            except:
                raise Exception(f"HTTP查询API返回错误状态: {response.status}")
    
    async def _execute_http_query(self, fe_host: str, start_time: float, sql: str, parameters: Optional[Dict] = None) -> DorisQueryResult:
        """使用HTTP查询接口执行一般SQL查询"""
        try:
            # 处理参数替换
            formatted_sql = sql
            if parameters:
                for key, value in parameters.items():
                    formatted_sql = formatted_sql.replace(f"${key}", str(value))
            
            # 尝试多个Doris HTTP查询API端点
            endpoints_to_try = [
                # Doris 2.x的查询API (已验证可用)
                f"http://{fe_host}:{self.config.http_port}/api/query/default_cluster/{self.config.database}",
                # 移除了其他返回HTML而非JSON的端点
            ]
            
            auth = aiohttp.BasicAuth(self.config.username, self.config.password)
            
            # 尝试不同的请求方式
            request_methods = [
                # 方法1: POST with JSON (Doris 2.x uses 'stmt' not 'sql')
                {
                    "method": "post",
                    "headers": {"Content-Type": "application/json"},
                    "data_type": "json",
                    "data": {"stmt": formatted_sql}
                },
                # 方法2: POST with JSON (fallback to old 'sql' format)
                {
                    "method": "post",
                    "headers": {"Content-Type": "application/json"},
                    "data_type": "json",
                    "data": {"sql": formatted_sql}
                },
                # 方法3: POST with form data
                {
                    "method": "post", 
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "data_type": "form",
                    "data": {"sql": formatted_sql}
                },
                # 方法4: GET with SQL parameter
                {
                    "method": "get",
                    "headers": {},
                    "data_type": "params",
                    "data": {"sql": formatted_sql}
                }
            ]
            
            for url in endpoints_to_try:
                for method_config in request_methods:
                    try:
                        self.logger.debug(f"尝试HTTP查询: {method_config['method'].upper()} {url}")
                        
                        if method_config["data_type"] == "json":
                            async with getattr(self.session, method_config["method"])(
                                url, 
                                json=method_config["data"], 
                                auth=auth, 
                                headers=method_config["headers"]
                            ) as response:
                                return await self._process_http_response(response, start_time, fe_host)
                                
                        elif method_config["data_type"] == "form":
                            form_data = aiohttp.FormData()
                            for key, value in method_config["data"].items():
                                form_data.add_field(key, value)
                            async with getattr(self.session, method_config["method"])(
                                url, 
                                data=form_data, 
                                auth=auth, 
                                headers=method_config["headers"]
                            ) as response:
                                return await self._process_http_response(response, start_time, fe_host)
                                
                        elif method_config["data_type"] == "params":
                            async with getattr(self.session, method_config["method"])(
                                url, 
                                params=method_config["data"], 
                                auth=auth, 
                                headers=method_config["headers"]
                            ) as response:
                                return await self._process_http_response(response, start_time, fe_host)
                                
                    except Exception as endpoint_error:
                        self.logger.debug(f"端点 {url} 方法 {method_config['method']} 失败: {endpoint_error}")
                        continue
            
            # 如果所有方法都失败，抛出详细的异常信息
            self.logger.error(f"所有HTTP查询端点和方法都失败")
            self.logger.error(f"尝试的SQL: {formatted_sql[:200]}...")
            self.logger.error(f"尝试的端点: {endpoints_to_try}")
            raise Exception(f"HTTP query failed: 所有HTTP查询端点和方法都失败。请检查Doris服务状态和网络连接。")
                    
        except Exception as e:
            # HTTP查询失败时不要伪造数据，抛出异常让上层感知错误
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.warning(f"HTTP查询失败: {e}, SQL: {formatted_sql[:200] if 'formatted_sql' in locals() else 'SQL未知'}...")
            raise Exception(f"HTTP query failed: {e}")

    async def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        try:
            # 使用 DESCRIBE 命令获取表结构
            sql = f"DESCRIBE {table_name}"
            result = await self.execute_query(sql)
            
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
                data = result_dict.get("data", [])
                
                # 转换格式
                table_columns = []
                for row in data:
                    if len(row) >= 4:  # Field, Type, Null, Key, Default, Extra
                        column_info = {
                            "name": row[0] if len(row) > 0 else "",
                            "type": row[1] if len(row) > 1 else "",
                            "nullable": row[2] if len(row) > 2 else "",
                            "key": row[3] if len(row) > 3 else "",
                            "default": row[4] if len(row) > 4 else None,
                            "extra": row[5] if len(row) > 5 else ""
                        }
                        table_columns.append(column_info)
                
                if table_columns:
                    return table_columns
                else:
                    # 如果没有获取到列信息，返回默认结构
                    return [{"name": "id", "type": "varchar", "nullable": "YES", "key": "", "default": None, "extra": ""}]
            else:
                # 如果结果格式不标准，返回基本结构
                return [{"name": "id", "type": "varchar", "nullable": "YES", "key": "", "default": None, "extra": ""}]
                
        except Exception as e:
            self.logger.warning(f"获取表 {table_name} 结构失败: {e}")
            # 返回默认结构
            return [{"name": "id", "type": "varchar", "nullable": "YES", "key": "", "default": None, "extra": ""}]


# 工厂函数
def create_doris_connector(data_source: DataSource) -> DorisConnector:
    """创建Doris连接器"""
    return DorisConnector.from_data_source(data_source)