from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.schemas.habit import HabitResponse

class PlanHabitCreate(BaseModel):
    habit_id: int
    time_window: Optional[str] = "anytime"
    day_config: Optional[str] = "everyday"

class PlanHabitResponse(BaseModel):
    id: int
    habit: HabitResponse
    time_window: Optional[str]
    day_config: Optional[str]

    class Config:
        from_attributes = True

class PlanCreate(BaseModel):
    name: str
    is_public: bool = False
    difficulty: str
    habits: List[PlanHabitCreate] = []

class PlanResponse(BaseModel):
    id: int
    name: str
    created_by: Optional[int]
    is_public: bool
    difficulty: str
    # Note: habit relationships could be loaded if needed

    class Config:
        from_attributes = True

class SelectPlanRequest(BaseModel):
    plan_id: int
    start_date: Optional[date] = None # Defaults to tomorrow in service if not provided
