from pydantic import BaseModel
from app.models.placeholder_mapping import PlaceholderType as ModelPlaceholderType

class PlaceholderType(str, ModelPlaceholderType):
    pass

class PlaceholderMappingBase(BaseModel):
    placeholder_name: str
    placeholder_description: str | None = None
    placeholder_type: PlaceholderType = ModelPlaceholderType.text
    data_source_id: int | None = None
    # Kept for backwards compatibility during transition
    data_source_query: str | None = None

class PlaceholderMappingCreate(PlaceholderMappingBase):
    pass

class PlaceholderMappingUpdate(PlaceholderMappingBase):
    pass

class PlaceholderMapping(PlaceholderMappingBase):
    id: int
    template_id: int

    class Config:
        orm_mode = True 