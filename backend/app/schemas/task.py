from datetime import datetime
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from cron_validator import CronValidator
from pydantic import BaseModel, field_validator, computed_field, field_serializer

# 导入Task状态枚举
from app.models.task import TaskStatus, ProcessingMode, AgentWorkflowType, ReportPeriod


class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: UUID
    data_source_id: UUID
    schedule: Optional[str] = None
    report_period: Optional[ReportPeriod] = ReportPeriod.MONTHLY
    recipients: Optional[List[str]] = []
    
    # 新增字段（可选，有默认值以保持向后兼容）
    processing_mode: Optional[ProcessingMode] = ProcessingMode.INTELLIGENT
    workflow_type: Optional[AgentWorkflowType] = AgentWorkflowType.SIMPLE_REPORT
    max_context_tokens: Optional[int] = 32000
    enable_compression: Optional[bool] = True

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
    data_source_id: Optional[UUID] = None
    schedule: Optional[str] = None
    report_period: Optional[ReportPeriod] = None
    recipients: Optional[List[str]] = None
    is_active: Optional[bool] = None
    
    # 新增字段
    processing_mode: Optional[ProcessingMode] = None
    workflow_type: Optional[AgentWorkflowType] = None
    max_context_tokens: Optional[int] = None
    enable_compression: Optional[bool] = None

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

    @computed_field
    @property
    def unique_id(self) -> str:
        return str(self.id)

    class Config:
        from_attributes = True


class TaskRead(TaskBase):
    id: int
    owner_id: UUID
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 新增字段
    status: Optional[TaskStatus] = None
    execution_count: Optional[int] = 0
    success_count: Optional[int] = 0
    failure_count: Optional[int] = 0
    success_rate: Optional[float] = 0.0
    last_execution_at: Optional[datetime] = None
    average_execution_time: Optional[float] = 0.0

    @computed_field
    @property
    def unique_id(self) -> str:
        return str(self.id)

    class Config:
        from_attributes = True


class TaskInDB(Task):
    pass


class TaskResponse(BaseModel):
    """Task response schema for API compatibility"""
    id: int
    name: str
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    data_source_id: Optional[UUID] = None
    schedule: Optional[str] = None
    report_period: str = "monthly"
    recipients: List[str] = []
    owner_id: Optional[UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 新增字段
    status: str = "pending"
    processing_mode: str = "intelligent"
    workflow_type: str = "simple_report"
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    last_execution_at: Optional[datetime] = None
    average_execution_time: float = 0.0
    max_context_tokens: int = 32000
    enable_compression: bool = True

    @computed_field
    @property
    def unique_id(self) -> str:
        return str(self.id)

    @field_serializer('template_id')
    def serialize_template_id(self, value: Optional[UUID]) -> Optional[str]:
        return str(value) if value else None

    @field_serializer('data_source_id')
    def serialize_data_source_id(self, value: Optional[UUID]) -> Optional[str]:
        return str(value) if value else None

    @field_serializer('owner_id')
    def serialize_owner_id(self, value: Optional[UUID]) -> Optional[str]:
        return str(value) if value else None

    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @field_serializer('updated_at')
    def serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @field_serializer('last_execution_at')
    def serialize_last_execution_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    class Config:
        from_attributes = True


# TaskExecution相关schemas
class TaskExecutionBase(BaseModel):
    task_id: int
    workflow_type: Optional[AgentWorkflowType] = AgentWorkflowType.SIMPLE_REPORT
    execution_context: Optional[Dict[str, Any]] = {}


class TaskExecutionCreate(TaskExecutionBase):
    celery_task_id: Optional[str] = None


class TaskExecutionUpdate(BaseModel):
    execution_status: Optional[TaskStatus] = None
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    error_details: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    output_artifacts: Optional[Dict[str, Any]] = None


class TaskExecutionResponse(TaskExecutionBase):
    id: int
    execution_id: UUID
    execution_status: TaskStatus
    progress_percentage: int = 0
    current_step: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration: Optional[int] = None
    error_details: Optional[str] = None
    celery_task_id: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
