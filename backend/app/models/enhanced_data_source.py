import enum

from sqlalchemy import JSON, Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DataSourceType(str, enum.Enum):
    sql = "sql"
    csv = "csv"
    api = "api"
    push = "push"  # 新增推送类型


class SQLQueryType(str, enum.Enum):
    single_table = "single_table"
    multi_table = "multi_table"  # 多表联查
    custom_view = "custom_view"


class EnhancedDataSource(Base):
    """增强版数据源模型，支持复杂SQL配置"""

    __tablename__ = "enhanced_data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True, nullable=False)
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

    # 状态管理
    is_active = Column(Boolean, default=True)
    last_sync_time = Column(String, nullable=True)

    # 外键
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 关联关系
    user = relationship("User", back_populates="enhanced_data_sources")
    etl_jobs = relationship("ETLJob", back_populates="enhanced_source")
    placeholder_mappings = relationship(
        "PlaceholderMapping", back_populates="data_source"
    )

    # 学习系统关系
    error_logs = relationship("ErrorLog", back_populates="data_source")
    learning_rules = relationship("LearningRule", back_populates="data_source")
    knowledge_entries = relationship("KnowledgeBase", back_populates="data_source")
    field_mapping_cache = relationship(
        "FieldMappingCache", back_populates="data_source"
    )
