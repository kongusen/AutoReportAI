import uuid
from typing import Any, Dict, Optional, List

from cron_validator import CronValidator
from pydantic import BaseModel, Field, field_validator, computed_field
from uuid import UUID
from datetime import datetime
from enum import Enum


class ETLJobStatus(str, Enum):
    """ETL Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ETLJobType(str, Enum):
    """ETL Job type enumeration"""
    DATA_EXTRACTION = "data_extraction"
    DATA_TRANSFORMATION = "data_transformation"
    DATA_LOADING = "data_loading"
    FULL_PIPELINE = "full_pipeline"


# Shared properties
class ETLJobBase(BaseModel):
    """ETL Job base schema"""
    name: str
    job_type: ETLJobType
    data_source_id: UUID
    configuration: Dict[str, Any]
    schedule: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        if v and not v.strip():
            raise ValueError("Schedule cannot be empty if provided")
        return v


# Properties to receive on item creation
class ETLJobCreate(ETLJobBase):
    """ETL Job creation schema"""
    pass


# Properties to receive on item update
class ETLJobUpdate(BaseModel):
    """ETL Job update schema"""
    name: Optional[str] = None
    job_type: Optional[ETLJobType] = None
    data_source_id: Optional[UUID] = None
    configuration: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Schedule cannot be empty if provided")
        return v


# Properties shared by models stored in DB
class ETLJobInDBBase(ETLJobBase):
    id: UUID
    user_id: UUID

    @computed_field
    @property
    def unique_id(self) -> str:
        return str(self.id)

    class Config:
        from_attributes = True


# Properties to return to client
class ETLJob(ETLJobInDBBase):
    pass


# Properties stored in DB
class ETLJobInDB(ETLJobInDBBase):
    """ETL Job database schema"""
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    status: ETLJobStatus = ETLJobStatus.PENDING
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None


# Alias for API response compatibility
ETLJobResponse = ETLJob
