from datetime import time
from pydantic import BaseModel
from typing import Optional
from app.models.enums import HabitCategory

class HabitCreate(BaseModel):
    name: str
    category: HabitCategory
    difficulty: Optional[str] = "easy"
    base_score: Optional[int] = 10
    is_public: bool = True
    
    # LifeOS v2 progression fields
    estimated_duration_minutes: Optional[int] = None
    frequency: Optional[str] = None
    habit_type: Optional[str] = None

class HabitResponse(BaseModel):
    id: int
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int
    created_by: int
    is_public: bool

    # Redesigned progression fields
    estimated_duration_minutes: int
    frequency: str
    habit_type: str
    difficulty_coefficient: float
    version: int

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
    
    # Lateness/Window parameters
    grace_period_minutes: int = 15
    late_threshold_minutes: int = 120

    class Config:
        from_attributes = True


class HabitDependencyCreate(BaseModel):
    parent_habit_id: int
    child_habit_id: int
    chain_order: Optional[int] = 1


class HabitDependencyResponse(BaseModel):
    id: int
    user_id: int
    parent_habit_id: int
    child_habit_id: int
    chain_order: int

    class Config:
        from_attributes = True