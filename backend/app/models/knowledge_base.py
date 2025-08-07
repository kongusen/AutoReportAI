from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)

    data_source = relationship("DataSource", back_populates="knowledge_bases") 