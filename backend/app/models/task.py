from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Task(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    schedule = Column(String, nullable=True)
    recipients = Column(String, nullable=True) # Comma-separated list of emails
    is_active = Column(Boolean, default=True)

    data_source_id = Column(Integer, ForeignKey("datasource.id"), nullable=False)
    data_source = relationship("DataSource")
    
    template_id = Column(Integer, ForeignKey("template.id"), nullable=False)
    template = relationship("Template") 