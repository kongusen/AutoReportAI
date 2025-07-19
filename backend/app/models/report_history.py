from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ReportHistory(Base):
    __tablename__ = "report_history"

    id = Column(Integer, primary_key=True, index=True)

    # The status of the report generation task (e.g., "success", "failure").
    status = Column(String, nullable=False)

    # The path to the generated .docx file.
    file_path = Column(String, nullable=True)

    # A detailed error message if the task failed.
    error_message = Column(Text, nullable=True)

    # Timestamp indicating when the report was generated.
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key to link this history record back to the task that triggered it.
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    # Foreign key to link this history record to the user who generated it.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    task = relationship("Task")
    user = relationship("User", back_populates="report_histories")
