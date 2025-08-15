"""
CSV文件连接器
支持CSV文件数据源的连接和查询
"""

import asyncio
import logging
import pandas as pd
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base_connector import BaseConnector, ConnectorConfig, QueryResult


@dataclass
class CSVConfig(ConnectorConfig):
    """CSV连接器配置"""
    file_path: str = None
    encoding: str = "utf-8"
    delimiter: str = ","
    has_header: bool = True
    chunk_size: int = 10000
    
    def __post_init__(self):
        if self.file_path is None:
            raise ValueError("file_path is required for CSVConfig")


class CSVConnector(BaseConnector):
    """CSV文件连接器"""
    
    def __init__(self, config: CSVConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._connected = False
        self._df: Optional[pd.DataFrame] = None
    
    async def connect(self) -> None:
        """建立CSV文件连接"""
        try:
            # 验证文件存在
            if not os.path.exists(self.config.file_path):
                raise FileNotFoundError(f"CSV file not found: {self.config.file_path}")
            
            # 读取文件头部验证格式
            self._df = pd.read_csv(
                self.config.file_path,
                encoding=self.config.encoding,
                sep=self.config.delimiter,
                nrows=1
            )
            
            self._connected = True
            self.logger.info(f"CSV connection established: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to CSV file: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开CSV文件连接"""
        self._df = None
        self._connected = False
        self.logger.info(f"CSV connection closed: {self.config.name}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试CSV文件连接"""
        try:
            if not self._connected:
                await self.connect()
            
            # 读取文件头部
            df = pd.read_csv(
                self.config.file_path,
                encoding=self.config.encoding,
                sep=self.config.delimiter,
                nrows=1
            )
            
            return {
                "success": True,
                "message": "CSV file access successful",
                "columns": df.columns.tolist(),
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"CSV file access failed: {str(e)}"
            }
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """执行CSV查询"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._connected:
                await self.connect()
            
            # 解析查询参数
            read_params = {
                "encoding": self.config.encoding,
                "sep": self.config.delimiter
            }
            
            if parameters:
                if "nrows" in parameters:
                    read_params["nrows"] = parameters["nrows"]
                if "skiprows" in parameters:
                    read_params["skiprows"] = parameters["skiprows"]
                if "usecols" in parameters:
                    read_params["usecols"] = parameters["usecols"]
            
            # 读取CSV文件
            df = pd.read_csv(self.config.file_path, **read_params)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return QueryResult(
                data=df,
                execution_time=execution_time,
                success=True,
                metadata={
                    "rows_returned": len(df),
                    "columns": df.columns.tolist(),
                    "file_size": os.path.getsize(self.config.file_path)
                }
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"CSV query failed: {e}")
            
            return QueryResult(
                data=pd.DataFrame(),
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取CSV字段列表"""
        try:
            if not self._connected:
                await self.connect()
            
            # 读取文件头部获取列名
            df = pd.read_csv(
                self.config.file_path,
                encoding=self.config.encoding,
                sep=self.config.delimiter,
                nrows=0
            )
            
            return df.columns.tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to get CSV fields: {e}")
            return []
    
    async def get_tables(self) -> List[str]:
        """CSV文件只有一个表，返回文件名"""
        return [os.path.basename(self.config.file_path)]
    
    async def get_data_preview(
        self, 
        table_name: Optional[str] = None, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取CSV数据预览"""
        try:
            result = await self.execute_query("", {"nrows": limit})
            
            if result.success:
                return {
                    "columns": result.data.columns.tolist(),
                    "data": result.data.to_dict(orient="records"),
                    "row_count": len(result.data),
                    "total_columns": len(result.data.columns),
                    "data_types": result.data.dtypes.astype(str).to_dict(),
                    "execution_time": result.execution_time,
                    "file_size": os.path.getsize(self.config.file_path)
                }
            else:
                return {
                    "error": result.error_message,
                    "columns": [],
                    "data": [],
                    "row_count": 0,
                    "total_columns": 0,
                    "data_types": {},
                    "execution_time": 0
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "columns": [],
                "data": [],
                "row_count": 0,
                "total_columns": 0,
                "data_types": {},
                "execution_time": 0
            }
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config.file_path:
            return False
        if not os.path.exists(self.config.file_path):
            return False
        return True
