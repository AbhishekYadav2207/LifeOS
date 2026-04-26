from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    timezone: str = "UTC"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    timezone: str

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    has_active_plan: bool
    active_plan_id: Optional[int] = None
