from pydantic import BaseModel
from typing import Optional

class HabitCreate(BaseModel):
    name: str
    category: str
    difficulty: str
    base_score: int = 10

class HabitResponse(BaseModel):
    id: int
    name: str
    category: str
    difficulty: str
    base_score: int

    class Config:
        from_attributes = True
