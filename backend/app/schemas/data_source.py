from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from app.models.data_source import DataSourceType

class DataSourceBase(BaseModel):
    name: str
    source_type: DataSourceType
    db_query: Optional[str] = None
    file_path: Optional[str] = None
    api_url: Optional[HttpUrl] = None
    api_method: Optional[str] = "GET"
    api_headers: Optional[Dict[str, Any]] = None
    api_body: Optional[Dict[str, Any]] = None

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(DataSourceBase):
    pass

class DataSource(DataSourceBase):
    id: int

    class Config:
        orm_mode = True 