from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from datetime import date, time
from app.schemas.habit import HabitResponse

class SelectPlanRequest(BaseModel):
    plan_id: int

class PlanHabitCreate(BaseModel):
    habit_id: int
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    day_config: Optional[str] = "everyday"

class PlanHabitResponse(BaseModel):
    id: int
    habit: HabitResponse
    start_time: Optional[time]
    end_time: Optional[time]
    day_config: Optional[str]

    class Config:
        from_attributes = True

class PlanCreate(BaseModel):
    name: str
    is_public: bool = False
    difficulty: str
    habits: List[PlanHabitCreate] = []

    @field_validator('habits', mode='before')
    @classmethod
    def parse_habits(cls, v):
        if not isinstance(v, list):
            return v
        new_habits = []
        for item in v:
            if isinstance(item, int):
                new_habits.append({"habit_id": item})
            else:
                new_habits.append(item)
        return new_habits

class PlanResponse(BaseModel):
    id: int
    name: str
    created_by: int
    is_public: bool
    difficulty: str
    habits_count: Optional[int] = None

    class Config:
        from_attributes = True
