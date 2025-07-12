from typing import Any, List, Optional

from pydantic import BaseModel


# Shared properties
class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None


# Properties to receive on item creation
class TemplateCreate(TemplateBase):
    pass


# Properties to receive on item update
class TemplateUpdate(TemplateBase):
    pass


# Properties shared by models stored in DB
class TemplateInDBBase(TemplateBase):
    id: int
    file_path: str
    parsed_structure: Optional[dict] = None

    class Config:
        orm_mode = True


# Properties to return to client
class Template(TemplateInDBBase):
    pass
