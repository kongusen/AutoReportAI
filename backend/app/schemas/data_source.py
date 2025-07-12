from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\- ]+$")
    description: Optional[str] = None
    type: str
    connection_params: Dict[str, Any]


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    description: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None


class DataSource(DataSourceBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True
