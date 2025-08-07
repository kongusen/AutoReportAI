"""Data Source schemas"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, validator


class DataSourceBase(BaseModel):
    """Data Source base schema"""

    name: str = Field(..., description="数据源名称")
    slug: Optional[str] = Field(None, description="用户友好的ID标识符")
    display_name: Optional[str] = Field(None, description="显示名称")
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
    # Doris相关字段
    doris_fe_hosts: Optional[List[str]] = Field(None, description="Doris FE节点列表")
    doris_be_hosts: Optional[List[str]] = Field(None, description="Doris BE节点列表")
    doris_http_port: Optional[int] = Field(8030, description="Doris HTTP端口")
    doris_query_port: Optional[int] = Field(9030, description="Doris查询端口")
    doris_database: Optional[str] = Field(None, description="Doris数据库名")
    doris_username: Optional[str] = Field(None, description="Doris用户名")
    doris_password: Optional[str] = Field(None, description="Doris密码")
    is_active: bool = Field(True, description="是否激活")

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("数据源名称不能为空")
        return v.strip()

    @validator("source_type")
    def validate_source_type(cls, v):
        valid_types = {"sql", "csv", "api", "push", "doris"}
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
    slug: Optional[str] = None
    display_name: Optional[str] = None
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
    # Doris相关字段
    doris_fe_hosts: Optional[List[str]] = None
    doris_be_hosts: Optional[List[str]] = None
    doris_http_port: Optional[int] = None
    doris_query_port: Optional[int] = None
    doris_database: Optional[str] = None
    doris_username: Optional[str] = None
    doris_password: Optional[str] = None
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
