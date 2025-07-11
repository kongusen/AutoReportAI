from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class User(UserInDB):
    pass 