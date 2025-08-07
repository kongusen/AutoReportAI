from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class FieldMappingCache(Base):
    __tablename__ = "field_mapping_cache"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)
    mapping_type = Column(String, nullable=False)
    mapping_value = Column(String, nullable=False)

    data_source = relationship("DataSource", back_populates="field_mapping_cache") 