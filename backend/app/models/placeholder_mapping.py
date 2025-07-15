import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlaceholderType(str, enum.Enum):
    text = "text"
    chart = "chart"
    table = "table"


class PlaceholderMapping(Base):
    __tablename__ = "placeholder_mappings"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(UUID(as_uuid=True), nullable=False)  # 临时移除外键约束以解决CI/CD问题
    placeholder_name = Column(String, index=True, nullable=False)
    placeholder_description = Column(String)
    placeholder_type = Column(
        Enum(PlaceholderType), nullable=False, default=PlaceholderType.text
    )

    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    
    # Relationships - 临时注释掉Template关系以解决CI/CD问题
    data_source = relationship("DataSource", back_populates="placeholder_mappings")
    # template = relationship("Template", back_populates="mappings")
