from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_serializer


class UserBase(BaseModel):
    id: Optional[UUID] = None
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class UserUpdate(BaseModel):
    id: Optional[UUID] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserInDBBase(UserBase):
    id: Optional[UUID] = None
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat() if value else None

    @field_serializer('updated_at')
    def serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    class Config:
        from_attributes = True


class User(UserInDBBase):
    id: Optional[UUID] = None

    class Config:
        from_attributes = True


class UserInDB(UserInDBBase):
    id: Optional[UUID] = None


class UserSchema(User):
    pass
