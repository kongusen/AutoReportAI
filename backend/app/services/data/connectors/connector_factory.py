"""
连接器工厂
根据数据源类型创建对应的连接器实例
"""

import logging
from typing import Dict, Any, Optional

from app.models.data_source import DataSource, DataSourceType
from .base_connector import BaseConnector
from .doris_connector import DorisConnector, DorisConfig
from .sql_connector import SQLConnector, SQLConfig
from .api_connector import APIConnector, APIConfig
from .csv_connector import CSVConnector, CSVConfig

logger = logging.getLogger(__name__)


def create_connector(data_source: DataSource) -> BaseConnector:
    """
    根据数据源创建对应的连接器
    
    Args:
        data_source: 数据源模型实例
        
    Returns:
        对应的连接器实例
    """
    try:
        if data_source.source_type == DataSourceType.doris:
            return _create_doris_connector(data_source)
        elif data_source.source_type == DataSourceType.sql:
            return _create_sql_connector(data_source)
        elif data_source.source_type == DataSourceType.api:
            return _create_api_connector(data_source)
        elif data_source.source_type == DataSourceType.csv:
            return _create_csv_connector(data_source)
        else:
            raise ValueError(f"Unsupported source type: {data_source.source_type}")
            
    except Exception as e:
        logger.error(f"Failed to create connector for data source {data_source.id}: {e}")
        raise


def _create_doris_connector(data_source: DataSource) -> DorisConnector:
    """创建Doris连接器"""
    from app.core.data_source_utils import DataSourcePasswordManager
    
    # 使用统一的密码管理器解密密码
    password = DataSourcePasswordManager.get_password(data_source.doris_password)
    logger.debug(f"Doris连接器密码处理完成，密码长度: {len(password)}")
    
    config = DorisConfig(
        source_type=data_source.source_type,
        name=data_source.name,
        description=data_source.display_name or data_source.name,
        fe_hosts=data_source.doris_fe_hosts or ["localhost"],
        be_hosts=data_source.doris_be_hosts or ["localhost"],
        http_port=data_source.doris_http_port or 8030,
        query_port=data_source.doris_query_port or 9030,
        database=data_source.doris_database or "default",
        username=data_source.doris_username or "root",
        password=password,
        load_balance=True,
        timeout=30,
        use_mysql_protocol=False  # 优先使用 HTTP API，因为更稳定
    )
    
    return DorisConnector(config)


def _create_sql_connector(data_source: DataSource) -> SQLConnector:
    """创建SQL连接器"""
    config = SQLConfig(
        source_type=data_source.source_type,
        name=data_source.name,
        description=data_source.display_name or data_source.name,
        connection_string=data_source.connection_string,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    return SQLConnector(config)


def _create_api_connector(data_source: DataSource) -> APIConnector:
    """创建API连接器"""
    config = APIConfig(
        source_type=data_source.source_type,
        name=data_source.name,
        description=data_source.display_name or data_source.name,
        api_url=data_source.api_url,
        method=data_source.api_method or "GET",
        headers=data_source.api_headers,
        body=data_source.api_body,
        timeout=30,
        auth_type="none",
        auth_credentials=None
    )
    
    return APIConnector(config)


def _create_csv_connector(data_source: DataSource) -> CSVConnector:
    """创建CSV连接器"""
    config = CSVConfig(
        source_type=data_source.source_type,
        name=data_source.name,
        description=data_source.display_name or data_source.name,
        file_path=getattr(data_source, 'file_path', None),
        encoding="utf-8",
        delimiter=",",
        has_header=True,
        chunk_size=10000
    )
    
    return CSVConnector(config)


def create_connector_from_config(
    source_type: str, 
    name: str, 
    config: Dict[str, Any]
) -> BaseConnector:
    """
    从配置字典创建连接器
    
    Args:
        source_type: 数据源类型
        name: 数据源名称
        config: 配置字典
        
    Returns:
        对应的连接器实例
    """
    try:
        if source_type == DataSourceType.doris:
            return _create_doris_connector_from_config(name, config)
        elif source_type == DataSourceType.sql:
            return _create_sql_connector_from_config(name, config)
        elif source_type == DataSourceType.api:
            return _create_api_connector_from_config(name, config)
        elif source_type == DataSourceType.csv:
            return _create_csv_connector_from_config(name, config)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
            
    except Exception as e:
        logger.error(f"Failed to create connector from config: {e}")
        raise


def _create_doris_connector_from_config(name: str, config: Dict[str, Any]) -> DorisConnector:
    """从配置创建Doris连接器"""
    doris_config = DorisConfig(
        source_type=DataSourceType.doris,
        name=name,
        description=config.get("description"),
        fe_hosts=config.get("fe_hosts", ["localhost"]),
        be_hosts=config.get("be_hosts", ["localhost"]),
        http_port=config.get("http_port", 8030),
        query_port=config.get("query_port", 9030),
        database=config.get("database", "default"),
        username=config.get("username", "root"),
        password=config.get("password", ""),
        load_balance=config.get("load_balance", True),
        timeout=config.get("timeout", 30)
    )
    
    return DorisConnector(doris_config)


def _create_sql_connector_from_config(name: str, config: Dict[str, Any]) -> SQLConnector:
    """从配置创建SQL连接器"""
    sql_config = SQLConfig(
        source_type=DataSourceType.sql,
        name=name,
        description=config.get("description"),
        connection_string=config["connection_string"],
        pool_size=config.get("pool_size", 5),
        max_overflow=config.get("max_overflow", 10),
        pool_pre_ping=config.get("pool_pre_ping", True),
        pool_recycle=config.get("pool_recycle", 3600),
        echo=config.get("echo", False)
    )
    
    return SQLConnector(sql_config)


def _create_api_connector_from_config(name: str, config: Dict[str, Any]) -> APIConnector:
    """从配置创建API连接器"""
    api_config = APIConfig(
        source_type=DataSourceType.api,
        name=name,
        description=config.get("description"),
        api_url=config["api_url"],
        method=config.get("method", "GET"),
        headers=config.get("headers"),
        body=config.get("body"),
        timeout=config.get("timeout", 30),
        auth_type=config.get("auth_type", "none"),
        auth_credentials=config.get("auth_credentials")
    )
    
    return APIConnector(api_config)


def _create_csv_connector_from_config(name: str, config: Dict[str, Any]) -> CSVConnector:
    """从配置创建CSV连接器"""
    csv_config = CSVConfig(
        source_type=DataSourceType.csv,
        name=name,
        description=config.get("description"),
        file_path=config["file_path"],
        encoding=config.get("encoding", "utf-8"),
        delimiter=config.get("delimiter", ","),
        has_header=config.get("has_header", True),
        chunk_size=config.get("chunk_size", 10000)
    )
    
    return CSVConnector(csv_config)
