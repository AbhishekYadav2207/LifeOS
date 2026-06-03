from datetime import time

from pydantic import BaseModel
from typing import Optional
from app.models.enums import HabitCategory

class HabitCreate(BaseModel):
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int = 10
    is_public: bool = True

class HabitResponse(BaseModel):
    id: int
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int
    created_by: int
    is_public: bool

    class Config:
        from_attributes = True

class PlanHabitTimelineResponse(BaseModel):
    id: int
    name: str
    category: str
    difficulty: str
    base_score: int

    start_time: time | None
    end_time: time | None
    day_config: str | None