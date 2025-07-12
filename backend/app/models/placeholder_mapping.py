import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlaceholderType(str, enum.Enum):
    text = "text"
    chart = "chart"
    table = "table"


class PlaceholderMapping(Base):
    __tablename__ = "placeholder_mappings"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    placeholder_name = Column(String, index=True, nullable=False)
    placeholder_description = Column(String)
    placeholder_type = Column(
        Enum(PlaceholderType), nullable=False, default=PlaceholderType.text
    )

    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    data_source = relationship("DataSource")

    # data_source_query is now deprecated and will be removed later
    # For now, we keep it for smoother transition
    data_source_query = Column(String, nullable=True)


# Add the relationship to the Template model
from .template import Template

Template.mappings = relationship(
    "PlaceholderMapping", back_populates="template", cascade="all, delete-orphan"
)
