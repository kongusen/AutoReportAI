from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class AnalyticsData(Base):
    __tablename__ = "analytics_data"

    id = Column(Integer, primary_key=True, index=True)

    # The unique identifier for the record from the original data source.
    # E.g., a primary key, a unique hash, or a composite key.
    record_id = Column(String, index=True, nullable=False)

    # The actual data record stored in a flexible JSON format.
    data = Column(JSON, nullable=False)

    # Timestamp indicating when the record was loaded into our system.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key to link this data record back to its source.
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)

    # Relationship to the DataSource model
    data_source = relationship("DataSource")
