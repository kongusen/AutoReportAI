import enum
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field


class DataSourceType(str, enum.Enum):
    sql = "sql"
    csv = "csv"
    api = "api"
    push = "push"

class SQLQueryType(str, enum.Enum):
    single_table = "single_table"
    multi_table = "multi_table"
    custom_view = "custom_view"


# Shared properties
class EnhancedDataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    source_type: DataSourceType
    connection_string: Optional[str] = None
    sql_query_type: SQLQueryType = SQLQueryType.single_table
    base_query: Optional[str] = None
    join_config: Optional[Dict[str, Any]] = None
    column_mapping: Optional[Dict[str, Any]] = None
    where_conditions: Optional[Dict[str, Any]] = None
    wide_table_name: Optional[str] = None
    wide_table_schema: Optional[Dict[str, Any]] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = "GET"
    api_headers: Optional[Dict[str, Any]] = None
    api_body: Optional[Dict[str, Any]] = None
    push_endpoint: Optional[str] = None
    push_auth_config: Optional[Dict[str, Any]] = None
    is_active: bool = True
    last_sync_time: Optional[str] = None


# Properties to receive on item creation
class EnhancedDataSourceCreate(EnhancedDataSourceBase):
    pass


# Properties to receive on item update
class EnhancedDataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source_type: Optional[DataSourceType] = None
    connection_string: Optional[str] = None
    sql_query_type: Optional[SQLQueryType] = None
    base_query: Optional[str] = None
    join_config: Optional[Dict[str, Any]] = None
    column_mapping: Optional[Dict[str, Any]] = None
    where_conditions: Optional[Dict[str, Any]] = None
    wide_table_name: Optional[str] = None
    wide_table_schema: Optional[Dict[str, Any]] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[Dict[str, Any]] = None
    api_body: Optional[Dict[str, Any]] = None
    push_endpoint: Optional[str] = None
    push_auth_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    last_sync_time: Optional[str] = None


# Properties shared by models stored in DB
class EnhancedDataSourceInDBBase(EnhancedDataSourceBase):
    id: int

    class Config:
        from_attributes = True


# Properties to return to client
class EnhancedDataSource(EnhancedDataSourceInDBBase):
    pass


# Properties stored in DB
class EnhancedDataSourceInDB(EnhancedDataSourceInDBBase):
    pass
