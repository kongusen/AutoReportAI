from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_superuser: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True


class User(UserInDB):
    pass
