from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DashboardStats(BaseModel):
    total_reports: int
    total_data_sources: int
    total_templates: int
    total_tasks: int
    active_tasks: int
    success_rate: float

class RecentActivity(BaseModel):
    id: str
    title: str
    status: str  # success, processing, failed
    timestamp: str
    type: str  # report, task, template

class SystemStatus(BaseModel):
    database: str
    ai_service: str
    redis: str
    timestamp: str 