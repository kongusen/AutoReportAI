import enum
import uuid

from sqlalchemy import JSON, Boolean, Column, Enum, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DataSourceType(str, enum.Enum):
    sql = "sql"
    csv = "csv"
    api = "api"
    push = "push"  # 新增推送类型
    doris = "doris"  # Apache Doris数据仓库


class SQLQueryType(str, enum.Enum):
    single_table = "single_table"
    multi_table = "multi_table"  # 多表联查
    custom_view = "custom_view"


class DataSource(Base):
    """数据源模型，支持复杂SQL配置"""

    __tablename__ = "data_sources"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, unique=True, nullable=False)
    slug = Column(String, index=True, nullable=True)  # 用户友好的ID，如 "my-doris-db"
    display_name = Column(String, index=True, nullable=True)  # 显示名称，如 "我的Doris数据库"
    source_type = Column(Enum(DataSourceType), nullable=False)

    # SQL配置增强
    connection_string = Column(String, nullable=True)
    sql_query_type = Column(Enum(SQLQueryType), default=SQLQueryType.single_table)

    # 复杂SQL配置
    base_query = Column(Text, nullable=True)  # 基础查询
    join_config = Column(JSON, nullable=True)  # 联表配置
    column_mapping = Column(JSON, nullable=True)  # 字段映射配置
    where_conditions = Column(JSON, nullable=True)  # 条件配置

    # 宽表配置
    wide_table_name = Column(String, nullable=True)  # 生成的宽表名称
    wide_table_schema = Column(JSON, nullable=True)  # 宽表结构定义

    # API配置
    api_url = Column(String, nullable=True)
    api_method = Column(String, default="GET", nullable=True)
    api_headers = Column(JSON, nullable=True)
    api_body = Column(JSON, nullable=True)

    # 推送配置（为将来扩展预留）
    push_endpoint = Column(String, nullable=True)
    push_auth_config = Column(JSON, nullable=True)
    
    # Doris配置
    doris_fe_hosts = Column(JSON, nullable=True)  # Frontend节点列表
    doris_be_hosts = Column(JSON, nullable=True)  # Backend节点列表  
    doris_http_port = Column(Integer, default=8030, nullable=True)  # HTTP端口
    doris_query_port = Column(Integer, default=9030, nullable=True)  # 查询端口
    doris_database = Column(String, nullable=True)  # 数据库名
    doris_username = Column(String, nullable=True)  # 用户名
    doris_password = Column(String, nullable=True)  # 密码（加密存储）

    # 状态管理
    is_active = Column(Boolean, default=True)
    last_sync_time = Column(String, nullable=True)

    # 外键
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 关联关系
    user = relationship("User", back_populates="data_sources")
    etl_jobs = relationship("ETLJob", back_populates="data_source")
    placeholder_mappings = relationship(
        "PlaceholderMapping", back_populates="data_source"
    )

    # 表结构关系
    table_schemas = relationship("TableSchema", back_populates="data_source", cascade="all, delete-orphan")
    table_relationships = relationship("TableRelationship", back_populates="data_source", cascade="all, delete-orphan")

    # 多库多表关系
    databases = relationship("Database", back_populates="data_source", cascade="all, delete-orphan")

    # 学习系统关系
    error_logs = relationship("ErrorLog", back_populates="data_source")
    learning_rules = relationship("LearningRule", back_populates="data_source")
    knowledge_entries = relationship("KnowledgeBase", back_populates="data_source")
    field_mapping_cache = relationship(
        "FieldMappingCache", back_populates="data_source"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def connection_config(self) -> dict:
        """动态构建连接配置以兼容现有代码"""
        if self.source_type == DataSourceType.doris:
            return {
                "source_type": "doris",
                "fe_hosts": self.doris_fe_hosts or ["localhost"],
                "http_port": self.doris_http_port or 8030,
                "query_port": self.doris_query_port or 9030,
                "database": self.doris_database or "default",
                "username": self.doris_username or "root",
                "password": self.doris_password or ""
            }
        elif self.source_type == DataSourceType.sql:
            return {
                "source_type": "sql",
                "connection_string": self.connection_string or "",
                "database": getattr(self, 'database_name', None) or "default"
            }
        elif self.source_type == DataSourceType.api:
            return {
                "source_type": "api",
                "api_url": self.api_url or "",
                "api_method": self.api_method or "GET",
                "api_headers": self.api_headers or {},
                "api_body": self.api_body or {}
            }
        else:
            return {
                "source_type": self.source_type.value if self.source_type else "unknown"
            }
