from pydantic import BaseModel
from typing import Optional

# Shared properties
class TaskBase(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = True

# Properties to receive on item creation
class TaskCreate(TaskBase):
    name: str
    schedule: str

# Properties to receive on item update
class TaskUpdate(TaskBase):
    pass

# Properties shared by models stored in DB
class TaskInDBBase(TaskBase):
    id: int
    name: str
    schedule: str
    enabled: bool

    class Config:
        orm_mode = True

# Properties to return to client
class Task(TaskInDBBase):
    pass 