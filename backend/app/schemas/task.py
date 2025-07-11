from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Shared properties
class TaskBase(BaseModel):
    name: str
    data_source_id: int
    template_id: int
    schedule: Optional[str] = None
    recipients: Optional[str] = None # Can be a comma-separated string of emails
    is_active: bool = True

# Properties to receive on task creation
class TaskCreate(TaskBase):
    pass

# Properties to receive on task update
class TaskUpdate(BaseModel):
    name: Optional[str] = None
    data_source_id: Optional[int] = None
    template_id: Optional[int] = None
    schedule: Optional[str] = None
    recipients: Optional[str] = None
    is_active: Optional[bool] = None

# Properties shared by models stored in DB
class TaskInDBBase(TaskBase):
    id: int

    class Config:
        orm_mode = True

# Properties to return to client
class Task(TaskInDBBase):
    pass 