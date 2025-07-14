from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


# Shared properties
class AnalyticsDataBase(BaseModel):
    record_id: str
    data: Dict[str, Any]
    data_source_id: int


# Properties to receive on creation
class AnalyticsDataCreate(AnalyticsDataBase):
    pass


# Properties to receive on update
class AnalyticsDataUpdate(BaseModel):
    record_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# Properties shared by models stored in DB
class AnalyticsDataInDBBase(AnalyticsDataBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Properties to return to client
class AnalyticsData(AnalyticsDataInDBBase):
    pass
