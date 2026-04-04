from pydantic import BaseModel
from typing import Optional
from app.models.enums import HabitCategory

class HabitCreate(BaseModel):
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int = 10

class HabitResponse(BaseModel):
    id: int
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int

    class Config:
        from_attributes = True
