"""
基础连接器接口
定义所有数据源连接器必须实现的接口
"""

import asyncio
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConnectorConfig:
    """连接器配置基类"""
    source_type: str
    name: str
    description: Optional[str] = None


@dataclass
class QueryResult:
    """查询结果基类"""
    data: pd.DataFrame
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        from app.utils.json_utils import convert_decimals

        data_dict = self.data.to_dict(orient="records") if not self.data.empty else []
        data_dict = convert_decimals(data_dict)

        return {
            "data": data_dict,
            "columns": self.data.columns.tolist() if not self.data.empty else [],
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
            "row_count": len(self.data)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResult':
        """从字典创建QueryResult对象"""
        df_data = data.get("data", [])
        columns = data.get("columns", [])
        
        if df_data and columns:
            df = pd.DataFrame(df_data, columns=columns)
        else:
            df = pd.DataFrame()
        
        return cls(
            data=df,
            execution_time=data.get("execution_time", 0.0),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


class BaseConnector(ABC):
    """基础连接器抽象类"""
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.logger = None  # 子类需要设置logger
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        pass
    
    @abstractmethod
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """执行查询"""
        pass
    
    @abstractmethod
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取字段列表"""
        pass
    
    @abstractmethod
    async def get_tables(self) -> List[str]:
        """获取表列表"""
        pass
    
    async def get_data_preview(
        self, 
        table_name: Optional[str] = None, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取数据预览"""
        try:
            if table_name:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
            else:
                query = f"SELECT * FROM (SELECT * FROM your_table LIMIT {limit}) AS preview"
            
            result = await self.execute_query(query)

            from app.utils.json_utils import convert_decimals

            data_dict = result.data.to_dict(orient="records")
            data_dict = convert_decimals(data_dict)

            return {
                "columns": result.data.columns.tolist(),
                "data": data_dict,
                "row_count": len(result.data),
                "total_columns": len(result.data.columns),
                "data_types": result.data.dtypes.astype(str).to_dict(),
                "execution_time": result.execution_time
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
        return True
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "source_type": self.config.source_type,
            "name": self.config.name,
            "description": self.config.description,
            "connected": hasattr(self, '_connected') and self._connected
        }
