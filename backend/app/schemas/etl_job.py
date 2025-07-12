import uuid
from typing import Any, Dict, Optional

from cron_validator import CronValidator
from pydantic import BaseModel, Field, field_validator


# Shared properties
class ETLJobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    source_data_source_id: int
    destination_table_name: str = Field(
        ..., pattern=r"^[a-zA-Z0-9_]+$", min_length=1, max_length=63
    )
    source_query: str
    transformation_config: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    enabled: bool = False

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        if v:
            try:
                CronValidator.parse(v)
            except ValueError:
                raise ValueError("Invalid cron expression")
        return v


# Properties to receive on item creation
class ETLJobCreate(ETLJobBase):
    pass


# Properties to receive on item update
class ETLJobUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    source_data_source_id: Optional[int] = None
    destination_table_name: Optional[str] = Field(
        None, pattern=r"^[a-zA-Z0-9_]+$", min_length=1, max_length=63
    )
    source_query: Optional[str] = None
    transformation_config: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        if v:
            try:
                CronValidator.parse(v)
            except ValueError:
                raise ValueError("Invalid cron expression")
        return v


# Properties shared by models stored in DB
class ETLJobInDBBase(ETLJobBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


# Properties to return to client
class ETLJob(ETLJobInDBBase):
    pass


# Properties stored in DB
class ETLJobInDB(ETLJobInDBBase):
    pass
