import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class ETLJob(Base):
    __tablename__ = "etl_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)

    enhanced_source_id = Column(
        Integer, ForeignKey("enhanced_data_sources.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    destination_table_name = Column(String, nullable=False, index=True)

    # The SQL query to execute on the source database
    source_query = Column(Text, nullable=False)

    # The structured (JSON) configuration for transformations
    transformation_config = Column(JSON, nullable=True)

    schedule = Column(String, nullable=True)  # Cron expression
    enabled = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="etl_jobs")
    enhanced_source = relationship("EnhancedDataSource", back_populates="etl_jobs")
