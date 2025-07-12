from sqlalchemy import JSON, Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(String, nullable=True)
    file_path = Column(String, unique=True)
    parsed_structure = Column(JSON)
    
    # Relationship to PlaceholderMapping
    mappings = relationship("PlaceholderMapping", back_populates="template", cascade="all, delete-orphan")
