from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

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
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系 - 临时简化以修复CI/CD
    # user = relationship("User", back_populates="templates")
    # mappings = relationship("PlaceholderMapping", back_populates="template", cascade="all, delete-orphan")
