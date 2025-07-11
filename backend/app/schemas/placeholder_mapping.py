from pydantic import BaseModel
from typing import Optional
from app.models.placeholder_mapping import PlaceholderType

# Shared properties
class PlaceholderMappingBase(BaseModel):
    placeholder_name: str
    placeholder_type: PlaceholderType
    source_logic: str
    description: Optional[str] = None

# Properties to receive on item creation
class PlaceholderMappingCreate(PlaceholderMappingBase):
    pass

# Properties to receive on item update
class PlaceholderMappingUpdate(PlaceholderMappingBase):
    pass

# Properties shared by models stored in DB
class PlaceholderMappingInDBBase(PlaceholderMappingBase):
    id: int
    template_id: int

    class Config:
        orm_mode = True

# Properties to return to client
class PlaceholderMapping(PlaceholderMappingInDBBase):
    pass 