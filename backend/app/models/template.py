import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    content = Column(Text)
    template_type = Column(String(50), default="docx")
    original_filename = Column(String(255))
    file_size = Column(Integer)
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系定义
    user = relationship("User", back_populates="templates")
    tasks = relationship("Task", back_populates="template")
    processing_history = relationship(
        "PlaceholderProcessingHistory", back_populates="template"
    )
    quality_scores = relationship("ReportQualityScore", back_populates="template")
