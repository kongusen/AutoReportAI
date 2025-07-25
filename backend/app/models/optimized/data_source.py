"""
优化的数据源模型
移除冗余字段，增强类型安全性
"""

import enum
from sqlalchemy import JSON, Boolean, Column, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import UserOwnedModel


class DataSourceType(str, enum.Enum):
    """数据源类型枚举"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    DORIS = "doris"
    CLICKHOUSE = "clickhouse"
    CSV = "csv"
    JSON_API = "json_api"
    EXCEL = "excel"


class ConnectionStatus(str, enum.Enum):
    """连接状态枚举"""
    PENDING = "pending"         # 待测试
    CONNECTED = "connected"     # 已连接
    FAILED = "failed"          # 连接失败
    TIMEOUT = "timeout"        # 连接超时


class DataSource(UserOwnedModel):
    """数据源模型"""
    
    __tablename__ = "data_sources"
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    source_type = Column(Enum(DataSourceType), nullable=False, index=True)
    
    # 连接配置（JSON存储，支持各种数据源类型）
    connection_config = Column(JSON, nullable=False)
    
    # 查询配置
    default_schema = Column(String(100), nullable=True)
    default_database = Column(String(100), nullable=True)
    
    # 状态管理
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.PENDING, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_tested_at = Column(String, nullable=True)
    last_sync_at = Column(String, nullable=True)
    
    # 性能配置
    connection_timeout = Column(Integer, default=30, nullable=False)
    query_timeout = Column(Integer, default=300, nullable=False)
    max_connections = Column(Integer, default=10, nullable=False)
    
    # 扩展配置
    tags = Column(JSON, nullable=True)  # 标签
    extra_metadata = Column(JSON, nullable=True)  # 扩展元数据
    
    # 关联关系
    etl_jobs = relationship("ETLJob", back_populates="data_source", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="data_source")
    
    @property
    def connection_string(self) -> str:
        """根据类型生成连接字符串"""
        config = self.connection_config or {}
        
        if self.source_type == DataSourceType.POSTGRESQL:
            return f"postgresql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port', 5432)}/{config.get('database')}"
        elif self.source_type == DataSourceType.MYSQL:
            return f"mysql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port', 3306)}/{config.get('database')}"
        elif self.source_type == DataSourceType.DORIS:
            return f"mysql://{config.get('username')}:{config.get('password')}@{config.get('fe_host')}:{config.get('query_port', 9030)}/{config.get('database')}"
        else:
            return ""
    
    @property
    def is_database_source(self) -> bool:
        """是否为数据库数据源"""
        return self.source_type in [
            DataSourceType.POSTGRESQL,
            DataSourceType.MYSQL,
            DataSourceType.DORIS,
            DataSourceType.CLICKHOUSE
        ]
    
    @property
    def is_file_source(self) -> bool:
        """是否为文件数据源"""
        return self.source_type in [
            DataSourceType.CSV,
            DataSourceType.EXCEL
        ]
    
    @property
    def is_api_source(self) -> bool:
        """是否为API数据源"""
        return self.source_type == DataSourceType.JSON_API
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return f"{self.name} ({self.source_type.value})"
    
    def to_connection_dict(self) -> dict:
        """转换为连接配置字典"""
        base_config = {
            'id': str(self.id),
            'name': self.name,
            'type': self.source_type.value,
            'status': self.status.value,
            'is_active': self.is_active
        }
        
        if self.connection_config:
            base_config.update(self.connection_config)
        
        return base_config