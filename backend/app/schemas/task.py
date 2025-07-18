import json
from typing import List, Optional
from uuid import UUID

from cron_validator import CronValidator
from pydantic import BaseModel, field_validator


class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: UUID
    data_source_id: int
    schedule: Optional[str] = None
    recipients: Optional[List[str]] = []

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: Optional[str]) -> Optional[str]:
        if v and not CronValidator.parse(v):
            raise ValueError("Invalid cron schedule format")
        return v

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            for email in v:
                if not ("@" in email and "." in email):
                    raise ValueError(f"Invalid email format: {email}")
        return v


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    data_source_id: Optional[int] = None
    schedule: Optional[str] = None
    recipients: Optional[List[str]] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: Optional[str]) -> Optional[str]:
        if v and not CronValidator.parse(v):
            raise ValueError("Invalid cron schedule format")
        return v

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            for email in v:
                if not ("@" in email and "." in email):
                    raise ValueError(f"Invalid email format: {email}")
        return v


class Task(TaskBase):
    id: int
    owner_id: UUID

    class Config:
        from_attributes = True


class TaskRead(TaskBase):
    id: int
    owner_id: UUID
    is_active: bool

    class Config:
        from_attributes = True
