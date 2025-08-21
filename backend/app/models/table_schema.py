"""
数据库元数据模型 - 支持多库多表的复杂数据架构
"""
import enum
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import (
    JSON, Boolean, Column, Enum, ForeignKey, Integer, 
    String, Text, DateTime, func, Index, UniqueConstraint,
    Float, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ColumnType(str, enum.Enum):
    """数据类型枚举"""
    INTEGER = "integer"
    BIGINT = "bigint"
    FLOAT = "float"
    DOUBLE = "double"
    DECIMAL = "decimal"
    STRING = "string"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    JSON = "json"
    ARRAY = "array"
    UNKNOWN = "unknown"


class TableType(str, enum.Enum):
    """表类型"""
    TABLE = "table"
    VIEW = "view" 
    MATERIALIZED_VIEW = "materialized_view"
    EXTERNAL_TABLE = "external_table"


class RelationType(str, enum.Enum):
    """关系类型"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class Database(Base):
    """数据库模型 - 数据源中的数据库"""
    __tablename__ = "databases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # 数据源关联
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    
    # 统计信息
    table_count = Column(Integer, default=0)
    total_size_mb = Column(BigInteger, default=0)
    
    # 业务分类
    business_domain = Column(String, nullable=True)  # 业务域：finance, hr, sales等
    data_sensitivity = Column(String, nullable=True)  # 敏感度级别
    
    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime, nullable=True)
    
    # 关系
    data_source = relationship("DataSource", back_populates="databases")
    tables = relationship("Table", back_populates="database", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('data_source_id', 'name', name='unique_database_per_source'),
        Index('idx_database_source_name', 'data_source_id', 'name'),
    )


class Table(Base):
    """表模型 - 数据库中的表"""
    __tablename__ = "tables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # 数据库关联
    database_id = Column(UUID(as_uuid=True), ForeignKey("databases.id"), nullable=False)
    
    # 表类型和引擎信息
    table_type = Column(Enum(TableType), default=TableType.TABLE)
    engine = Column(String, nullable=True)  # 存储引擎
    charset = Column(String, nullable=True)  # 字符集
    
    # 统计信息
    row_count = Column(BigInteger, default=0)
    size_mb = Column(Float, default=0.0)
    column_count = Column(Integer, default=0)
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime, nullable=True)
    
    # 业务标签
    business_tags = Column(JSON, nullable=True)  # 业务标签，如 ["用户", "订单", "核心表"]
    data_sensitivity = Column(String, nullable=True)  # 数据敏感度: public, internal, confidential, restricted
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    # 关系
    database = relationship("Database", back_populates="tables")
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    indexes = relationship("TableIndex", back_populates="table", cascade="all, delete-orphan")
    relations_as_parent = relationship("TableRelation", foreign_keys="TableRelation.parent_table_id")
    relations_as_child = relationship("TableRelation", foreign_keys="TableRelation.child_table_id")
    
    __table_args__ = (
        UniqueConstraint('database_id', 'name', name='unique_table_per_database'),
        Index('idx_table_database_name', 'database_id', 'name'),
        Index('idx_table_business_tags', 'business_tags'),
    )


class TableColumn(Base):
    """表字段模型"""
    __tablename__ = "table_columns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    
    # 表关联
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False)
    
    # 数据类型信息
    data_type = Column(Enum(ColumnType), nullable=False)
    raw_type = Column(String, nullable=False)  # 原始数据类型
    max_length = Column(Integer, nullable=True)
    precision = Column(Integer, nullable=True)
    scale = Column(Integer, nullable=True)
    
    # 约束信息
    is_nullable = Column(Boolean, default=True)
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    default_value = Column(String, nullable=True)
    
    # 注释和业务语义
    column_comment = Column(Text, nullable=True)
    business_meaning = Column(String, nullable=True)  # 业务含义
    
    # 位置信息
    ordinal_position = Column(Integer, nullable=False)
    
    # 统计信息
    null_count = Column(BigInteger, nullable=True)
    unique_count = Column(BigInteger, nullable=True)
    distinct_count = Column(BigInteger, nullable=True)
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    table = relationship("Table", back_populates="columns")
    
    __table_args__ = (
        UniqueConstraint('table_id', 'name', name='unique_column_per_table'),
        Index('idx_column_table_name', 'table_id', 'name'),
        Index('idx_column_ordinal', 'table_id', 'ordinal_position'),
    )


class TableIndex(Base):
    """表索引模型"""
    __tablename__ = "table_indexes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    
    # 表关联
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False)
    
    # 索引信息
    index_type = Column(String, nullable=True)  # 索引类型：btree, hash, gist等
    is_unique = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    columns = Column(JSON, nullable=False)  # 索引字段列表
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    table = relationship("Table", back_populates="indexes")
    
    __table_args__ = (
        UniqueConstraint('table_id', 'name', name='unique_index_per_table'),
    )


class TableRelation(Base):
    """表关系模型"""
    __tablename__ = "table_relations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    
    # 关系表
    parent_table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False)
    child_table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False)
    
    # 关系类型
    relation_type = Column(Enum(RelationType), nullable=False)
    
    # 关联字段
    parent_columns = Column(JSON, nullable=False)  # 父表字段列表
    child_columns = Column(JSON, nullable=False)   # 子表字段列表
    
    # 关系强度和置信度
    confidence_score = Column(Float, default=0.0)  # 关系置信度 0-1
    is_validated = Column(Boolean, default=False)  # 是否已验证
    
    # 业务语义
    business_meaning = Column(Text, nullable=True)
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    parent_table = relationship("Table", foreign_keys=[parent_table_id])
    child_table = relationship("Table", foreign_keys=[child_table_id])
    
    __table_args__ = (
        UniqueConstraint('parent_table_id', 'child_table_id', 'name', name='unique_relation'),
        Index('idx_relation_parent', 'parent_table_id'),
        Index('idx_relation_child', 'child_table_id'),
    )


# 兼容性模型 - 保持向后兼容
class TableSchema(Base):
    """表结构模型，存储数据源中表的元数据信息"""
    
    __tablename__ = "table_schemas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 关联数据源
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    
    # 表基本信息
    table_name = Column(String, nullable=False, index=True)
    table_schema = Column(String, nullable=True)  # 数据库schema名
    table_catalog = Column(String, nullable=True)  # 数据库catalog名
    
    # 表结构信息
    columns_info = Column(JSON, nullable=False)  # 列信息列表
    primary_keys = Column(JSON, nullable=True)  # 主键列名列表
    indexes = Column(JSON, nullable=True)  # 索引信息
    constraints = Column(JSON, nullable=True)  # 约束信息
    
    # 统计信息
    estimated_row_count = Column(BigInteger, nullable=True)  # 预估行数
    table_size_bytes = Column(BigInteger, nullable=True)  # 表大小（字节）
    last_analyzed = Column(DateTime(timezone=True), nullable=True)  # 最后分析时间
    
    # 业务分类信息
    business_category = Column(String, nullable=True)  # 业务分类（如：用户、订单、产品等）
    data_freshness = Column(String, nullable=True)  # 数据新鲜度（如：实时、准实时、离线）
    update_frequency = Column(String, nullable=True)  # 更新频率
    
    # 数据质量信息
    data_quality_score = Column(Float, nullable=True)  # 数据质量评分
    completeness_rate = Column(Float, nullable=True)  # 完整率
    accuracy_rate = Column(Float, nullable=True)  # 准确率
    
    # 状态管理
    is_active = Column(Boolean, default=True)
    is_analyzed = Column(Boolean, default=False)  # 是否已进行深度分析
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    data_source = relationship("DataSource", back_populates="table_schemas")
    columns = relationship("ColumnSchema", back_populates="table_schema", cascade="all, delete-orphan")


class ColumnSchema(Base):
    """列结构模型，存储表中列的详细信息"""
    
    __tablename__ = "column_schemas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 关联表结构
    table_schema_id = Column(UUID(as_uuid=True), ForeignKey("table_schemas.id"), nullable=False)
    
    # 列基本信息
    column_name = Column(String, nullable=False, index=True)
    column_type = Column(String, nullable=False)  # 原始数据类型
    normalized_type = Column(String(50), nullable=False)  # 标准化类型
    column_size = Column(Integer, nullable=True)  # 列大小/长度
    precision = Column(Integer, nullable=True)  # 精度（用于decimal类型）
    scale = Column(Integer, nullable=True)  # 小数位数
    
    # 约束信息
    is_nullable = Column(Boolean, default=True)
    is_primary_key = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    default_value = Column(String, nullable=True)
    
    # 业务语义信息
    business_name = Column(String, nullable=True)  # 业务名称（中文）
    business_description = Column(Text, nullable=True)  # 业务描述
    semantic_category = Column(String, nullable=True)  # 语义分类（如：ID、名称、时间、金额等）
    
    # 数据质量信息
    null_count = Column(BigInteger, nullable=True)  # NULL值数量
    unique_count = Column(BigInteger, nullable=True)  # 唯一值数量
    distinct_count = Column(BigInteger, nullable=True)  # 不同值数量
    min_value = Column(String, nullable=True)  # 最小值
    max_value = Column(String, nullable=True)  # 最大值
    avg_value = Column(String, nullable=True)  # 平均值（数值类型）
    
    # 数据模式信息
    data_patterns = Column(JSON, nullable=True)  # 数据模式（如：邮箱格式、手机号格式等）
    sample_values = Column(JSON, nullable=True)  # 样本值
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    table_schema = relationship("TableSchema", back_populates="columns")


class TableRelationship(Base):
    """表关系模型，存储表之间的关联关系"""
    
    __tablename__ = "table_relationships"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 关联数据源
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    
    # 关系信息
    source_table_id = Column(UUID(as_uuid=True), ForeignKey("table_schemas.id"), nullable=False)
    target_table_id = Column(UUID(as_uuid=True), ForeignKey("table_schemas.id"), nullable=False)
    
    # 关系类型
    relationship_type = Column(String, nullable=False)  # 关系类型：one_to_one, one_to_many, many_to_many
    
    # 关联字段
    source_column = Column(String, nullable=False)  # 源表关联字段
    target_column = Column(String, nullable=False)  # 目标表关联字段
    
    # 关系强度
    confidence_score = Column(Float, nullable=True)  # 关系置信度（0-1）
    
    # 业务描述
    business_description = Column(Text, nullable=True)  # 业务关系描述
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    data_source = relationship("DataSource", back_populates="table_relationships")
    source_table = relationship("TableSchema", foreign_keys=[source_table_id])
    target_table = relationship("TableSchema", foreign_keys=[target_table_id])