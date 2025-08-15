"""
数据源连接器模块
提供统一的数据源连接接口
"""

from .base_connector import BaseConnector, ConnectorConfig, QueryResult
from .doris_connector import DorisConnector, DorisConfig, DorisQueryResult
from .sql_connector import SQLConnector, SQLConfig
from .api_connector import APIConnector, APIConfig
from .csv_connector import CSVConnector, CSVConfig
from .connector_factory import create_connector, create_connector_from_config

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "QueryResult",
    "DorisConnector",
    "DorisConfig",
    "DorisQueryResult",
    "SQLConnector",
    "SQLConfig",
    "APIConnector", 
    "APIConfig",
    "CSVConnector",
    "CSVConfig",
    "create_connector",
    "create_connector_from_config"
]
