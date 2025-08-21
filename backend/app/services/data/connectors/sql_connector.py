"""
SQL数据库连接器
支持各种SQL数据库的连接和查询
"""

import asyncio
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .base_connector import BaseConnector, ConnectorConfig, QueryResult
from app.core.security_utils import decrypt_data


@dataclass
class SQLConfig(ConnectorConfig):
    """SQL连接器配置"""
    connection_string: str = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_recycle: int = 3600
    echo: bool = False
    
    def __post_init__(self):
        if self.connection_string is None:
            raise ValueError("connection_string is required for SQLConfig")


class SQLConnector(BaseConnector):
    """SQL数据库连接器"""
    
    def __init__(self, config: SQLConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.engine: Optional[Engine] = None
        self._connected = False
    
    async def connect(self) -> None:
        """建立数据库连接"""
        try:
            # 解密连接字符串
            connection_string = decrypt_data(self.config.connection_string)
            
            # 创建引擎
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=self.config.pool_pre_ping,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
            )
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._connected = True
            self.logger.info(f"SQL connection established: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SQL database: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self._connected = False
        self.logger.info(f"SQL connection closed: {self.config.name}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            if not self.engine:
                await self.connect()
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()[0]
                
                if test_value == 1:
                    return {
                        "success": True,
                        "message": "SQL connection successful",
                        "timestamp": asyncio.get_event_loop().time()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Unexpected test result"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"SQL connection failed: {str(e)}"
            }
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """执行SQL查询"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.engine:
                await self.connect()
            
            # 执行查询
            df = pd.read_sql(query, self.engine, params=parameters)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return QueryResult(
                data=df,
                execution_time=execution_time,
                success=True,
                metadata={
                    "rows_returned": len(df),
                    "columns": df.columns.tolist()
                }
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"SQL query failed: {e}")
            
            return QueryResult(
                data=pd.DataFrame(),
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取字段列表"""
        try:
            if not self.engine:
                await self.connect()
            
            if table_name:
                # 获取指定表的字段
                query = f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
                """
            else:
                # 获取所有字段
                query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE()
                ORDER BY table_name, ordinal_position
                """
            
            df = pd.read_sql(query, self.engine)
            return df['column_name'].tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to get SQL fields: {e}")
            return []
    
    async def get_tables(self) -> List[str]:
        """获取表列表"""
        try:
            if not self.engine:
                await self.connect()
            
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            ORDER BY table_name
            """
            
            df = pd.read_sql(query, self.engine)
            return df['table_name'].tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to get SQL tables: {e}")
            return []
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config.connection_string:
            return False
        return True
