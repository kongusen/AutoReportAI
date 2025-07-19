"""
占位符映射数据模型

用于存储占位符字段映射的历史记录和缓存信息
"""

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base_class import Base


class PlaceholderMapping(Base):
    """占位符映射表"""

    __tablename__ = "placeholder_mapping_cache"

    id = Column(Integer, primary_key=True, index=True)
    placeholder_signature = Column(String(255), unique=True, nullable=False, index=True)
    data_source_id = Column(
        Integer, ForeignKey("enhanced_data_sources.id"), nullable=False
    )
    matched_field = Column(String(255), nullable=False)
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    transformation_config = Column(JSON, nullable=True)
    usage_count = Column(Integer, default=1, nullable=False)
    last_used_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    data_source = relationship(
        "EnhancedDataSource", back_populates="placeholder_mappings"
    )
