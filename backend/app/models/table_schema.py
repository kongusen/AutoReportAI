import enum
import uuid
from typing import Dict, Any

from sqlalchemy import JSON, Boolean, Column, Enum, ForeignKey, Integer, String, Text, DateTime, func, BigInteger, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ColumnType(str, enum.Enum):
    """列数据类型枚举"""
    # 数值类型
    INT = "int"
    BIGINT = "bigint"
    FLOAT = "float"
    DOUBLE = "double"
    DECIMAL = "decimal"
    
    # 字符串类型
    VARCHAR = "varchar"
    CHAR = "char"
    TEXT = "text"
    
    # 日期时间类型
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    
    # 布尔类型
    BOOLEAN = "boolean"
    
    # 其他类型
    JSON = "json"
    ARRAY = "array"
    UNKNOWN = "unknown"


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
    
    def __repr__(self):
        return f"<TableSchema(id={self.id}, table_name='{self.table_name}', data_source_id={self.data_source_id})>"


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
    normalized_type = Column(Enum(ColumnType), nullable=False)  # 标准化类型
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
    
    def __repr__(self):
        return f"<ColumnSchema(id={self.id}, column_name='{self.column_name}', table_schema_id={self.table_schema_id})>"


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
    
    def __repr__(self):
        return f"<TableRelationship(id={self.id}, source_table_id={self.source_table_id}, target_table_id={self.target_table_id})>"
