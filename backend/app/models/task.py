from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    schedule = Column(String, nullable=True)
    recipients = Column(JSON, nullable=True)  # Store list of emails as JSON
    is_active = Column(Boolean, default=True)

    # Foreign key relationships
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="tasks", foreign_keys=[owner_id])
    data_source = relationship("DataSource")
    template = relationship("Template", back_populates="tasks")
