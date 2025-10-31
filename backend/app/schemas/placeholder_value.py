"""
Pydantic schemas for PlaceholderValue

占位符值的数据模型定义
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class PlaceholderValueBase(BaseModel):
    """占位符值基础模型"""
    placeholder_id: UUID
    data_source_id: UUID
    raw_query_result: Optional[Dict[str, Any]] = None
    processed_value: Optional[Dict[str, Any]] = None
    formatted_text: Optional[str] = None
    execution_sql: Optional[str] = None
    execution_time_ms: Optional[int] = None
    row_count: int = 0
    success: bool = True
    error_message: Optional[str] = None
    source: str = "etl"
    confidence_score: float = 1.0
    analysis_metadata: Optional[Dict[str, Any]] = None


class PlaceholderValueCreate(PlaceholderValueBase):
    """创建占位符值"""
    execution_time: Optional[datetime] = None
    report_period: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    sql_parameters_snapshot: Optional[Dict[str, Any]] = None
    execution_batch_id: Optional[str] = None
    version_hash: Optional[str] = None
    is_latest_version: bool = True
    cache_key: Optional[str] = None
    expires_at: Optional[datetime] = None


class PlaceholderValueUpdate(BaseModel):
    """更新占位符值"""
    is_latest_version: Optional[bool] = None
    hit_count: Optional[int] = None
    last_hit_at: Optional[datetime] = None


class PlaceholderValueInDB(PlaceholderValueBase):
    """数据库中的占位符值"""
    id: UUID
    execution_time: Optional[datetime] = None
    report_period: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    sql_parameters_snapshot: Optional[Dict[str, Any]] = None
    execution_batch_id: Optional[str] = None
    version_hash: Optional[str] = None
    is_latest_version: bool = True
    cache_key: Optional[str] = None
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    last_hit_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlaceholderValueResponse(PlaceholderValueInDB):
    """占位符值响应模型"""
    pass
