from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    schedule = Column(String, nullable=True)
    recipients = Column(JSON, nullable=True)  # Store list of emails as JSON
    is_active = Column(Boolean, default=True)

    # Foreign key relationships
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)

    # Relationships - 临时简化以修复CI/CD
    # user = relationship("User", back_populates="tasks", foreign_keys=[owner_id])
    # data_source = relationship("DataSource")
    # template = relationship("Template")
