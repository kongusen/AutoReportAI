from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# Shared properties
class ReportHistoryBase(BaseModel):
    task_id: int
    user_id: UUID
    status: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None


# Properties to receive on creation
class ReportHistoryCreate(ReportHistoryBase):
    pass


# Properties shared by models stored in DB
class ReportHistoryInDBBase(ReportHistoryBase):
    id: int
    generated_at: datetime

    class Config:
        from_attributes = True


# Properties to return to client
class ReportHistory(ReportHistoryInDBBase):
    pass
