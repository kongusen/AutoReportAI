from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\- ]+$")
    source_type: str = Field(..., description="Type of data source: sql, csv, or api")
    
    # For 'sql' type
    connection_string: Optional[str] = Field(None, description="Database connection string for sql type sources")
    db_query: Optional[str] = Field(None, description="SQL query for sql type sources")
    
    # For 'csv' type
    file_path: Optional[str] = Field(None, description="File path for csv type sources")
    
    # For 'api' type
    api_url: Optional[str] = Field(None, description="API URL for api type sources")
    api_method: Optional[str] = Field("GET", description="HTTP method for API calls")
    api_headers: Optional[Dict[str, Any]] = Field(None, description="HTTP headers for API calls")
    api_body: Optional[Dict[str, Any]] = Field(None, description="HTTP body for API calls")


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\- ]+$")
    source_type: Optional[str] = Field(None, description="Type of data source: sql, csv, or api")
    connection_string: Optional[str] = Field(None, description="Database connection string for sql type sources")
    db_query: Optional[str] = Field(None, description="SQL query for sql type sources")
    file_path: Optional[str] = Field(None, description="File path for csv type sources")
    api_url: Optional[str] = Field(None, description="API URL for api type sources")
    api_method: Optional[str] = Field(None, description="HTTP method for API calls")
    api_headers: Optional[Dict[str, Any]] = Field(None, description="HTTP headers for API calls")
    api_body: Optional[Dict[str, Any]] = Field(None, description="HTTP body for API calls")


class DataSource(DataSourceBase):
    id: int

    class Config:
        from_attributes = True
