"""
占位符映射Pydantic模式
"""

from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

from pydantic import BaseModel, Field


class PlaceholderType(str, Enum):
    """占位符类型枚举"""
    SIMPLE = "simple"
    AGGREGATE = "aggregate"
    COMPLEX = "complex"
    LIST = "list"
    CONDITIONAL = "conditional"


class PlaceholderMatch(BaseModel):
    """占位符匹配结果"""
    name: str = Field(..., description="占位符名称")
    description: str = Field(..., description="占位符描述")
    placeholder_type: PlaceholderType = Field(..., description="占位符类型")
    required_fields: list[str] = Field(default_factory=list, description="需要的字段")
    sql_pattern: Optional[str] = Field(None, description="SQL模式")
    confidence: float = Field(default=0.0, description="匹配置信度")


class PlaceholderMappingBase(BaseModel):
    """占位符映射基础模式"""

    placeholder_signature: str = Field(..., description="占位符签名")
    data_source_id: int = Field(..., description="数据源ID")
    matched_field: str = Field(..., description="匹配的字段名")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    transformation_config: Optional[Dict[str, Any]] = Field(
        None, description="转换配置"
    )


class PlaceholderMappingCreate(PlaceholderMappingBase):
    """创建占位符映射"""

    usage_count: int = Field(1, description="使用次数")


class PlaceholderMappingUpdate(BaseModel):
    """更新占位符映射"""

    matched_field: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    transformation_config: Optional[Dict[str, Any]] = None
    usage_count: Optional[int] = None


class PlaceholderMappingInDBBase(PlaceholderMappingBase):
    """数据库中的占位符映射基础模式"""

    id: int
    usage_count: int
    last_used_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PlaceholderMapping(PlaceholderMappingInDBBase):
    """占位符映射完整模式"""

    pass


class PlaceholderMappingInDB(PlaceholderMappingInDBBase):
    """数据库中的占位符映射"""

    pass
