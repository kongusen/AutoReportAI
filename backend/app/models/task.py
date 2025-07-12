from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON
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
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)

    # Relationships
    owner = relationship("User")
    data_source = relationship("DataSource")
    template = relationship("Template")
