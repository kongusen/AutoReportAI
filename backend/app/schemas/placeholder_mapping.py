from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.placeholder_mapping import PlaceholderType as ModelPlaceholderType


class PlaceholderType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        if v not in {item.value for item in ModelPlaceholderType}:
            raise ValueError(f"Invalid placeholder type: {v}")
        return v


class PlaceholderMappingBase(BaseModel):
    placeholder_key: str
    placeholder_type: PlaceholderType
    description: Optional[str] = None
    sample_data: Optional[str] = None


class PlaceholderMappingCreate(PlaceholderMappingBase):
    pass


class PlaceholderMappingUpdate(BaseModel):
    description: Optional[str] = None
    sample_data: Optional[str] = None


class PlaceholderMapping(PlaceholderMappingBase):
    id: int
    template_id: int
    owner_id: int

    class Config:
        from_attributes = True
