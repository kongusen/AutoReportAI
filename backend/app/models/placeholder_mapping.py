from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class PlaceholderType(str, enum.Enum):
    QUERY = "query"
    COMPUTED = "computed"
    CHART = "chart"
    TABLE = "table"

class PlaceholderMapping(Base):
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("template.id"))
    placeholder_name = Column(String, index=True)
    placeholder_type = Column(SAEnum(PlaceholderType))
    source_logic = Column(String, nullable=False) # Stores SQL query or computation key
    description = Column(String, nullable=True)
    
    template = relationship("Template", back_populates="mappings")

# Add the relationship to the Template model
from .template import Template
Template.mappings = relationship("PlaceholderMapping", back_populates="template", cascade="all, delete-orphan") 