"""Data Source schemas"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, validator


class DataSourceBase(BaseModel):
    """Data Source base schema"""

    name: str = Field(..., description="数据源名称")
    source_type: str = Field(..., description="数据源类型")
    connection_string: Optional[str] = Field(None, description="数据库连接字符串")
    sql_query_type: str = Field("single_table", description="SQL查询类型")
    base_query: Optional[str] = Field(None, description="基础查询")
    join_config: Optional[Dict[str, Any]] = Field(None, description="连接配置")
    column_mapping: Optional[Dict[str, Any]] = Field(None, description="列映射配置")
    where_conditions: Optional[Dict[str, Any]] = Field(None, description="条件配置")
    wide_table_name: Optional[str] = Field(None, description="宽表名称")
    wide_table_schema: Optional[Dict[str, Any]] = Field(None, description="宽表模式")
    api_url: Optional[str] = Field(None, description="API URL")
    api_method: Optional[str] = Field("GET", description="API方法")
    api_headers: Optional[Dict[str, str]] = Field(None, description="API头部")
    api_body: Optional[Dict[str, Any]] = Field(None, description="API请求体")
    push_endpoint: Optional[str] = Field(None, description="推送端点")
    push_auth_config: Optional[Dict[str, Any]] = Field(None, description="推送认证配置")
    is_active: bool = Field(True, description="是否激活")

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("数据源名称不能为空")
        return v.strip()

    @validator("source_type")
    def validate_source_type(cls, v):
        valid_types = {"sql", "csv", "api", "push"}
        if v not in valid_types:
            raise ValueError(f"数据源类型必须是 {valid_types} 之一")
        return v

    @validator("sql_query_type")
    def validate_sql_query_type(cls, v):
        valid_types = {"single_table", "multi_table", "custom_view"}
        if v not in valid_types:
            raise ValueError(f"SQL查询类型必须是 {valid_types} 之一")
        return v


class DataSourceCreate(DataSourceBase):
    """Data Source create schema"""
    pass


class DataSourceUpdate(BaseModel):
    """Data Source update schema"""

    name: Optional[str] = None
    connection_string: Optional[str] = None
    sql_query_type: Optional[str] = None
    base_query: Optional[str] = None
    join_config: Optional[Dict[str, Any]] = None
    column_mapping: Optional[Dict[str, Any]] = None
    where_conditions: Optional[Dict[str, Any]] = None
    wide_table_name: Optional[str] = None
    wide_table_schema: Optional[Dict[str, Any]] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[Dict[str, str]] = None
    api_body: Optional[Dict[str, Any]] = None
    push_endpoint: Optional[str] = None
    push_auth_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @validator("name")
    def validate_name(cls, v):
        if v is not None and (not v or len(v.strip()) == 0):
            raise ValueError("数据源名称不能为空")
        return v.strip() if v else v


class DataSource(DataSourceBase):
    """Data Source response schema"""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    @property
    def unique_id(self) -> str:
        return str(self.id)

    model_config = {
        "from_attributes": True
    }


class DataSourceResponse(DataSource):
    """Data Source API response schema"""
    pass
