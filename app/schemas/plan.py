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
    grace_period_minutes: Optional[int] = 15
    late_threshold_minutes: Optional[int] = 120

class PlanHabitResponse(BaseModel):
    id: int
    habit: HabitResponse
    start_time: Optional[time]
    end_time: Optional[time]
    day_config: Optional[str]
    grace_period_minutes: int
    late_threshold_minutes: int

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

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Morning Routine Plan",
                "is_public": True,
                "difficulty": "medium",
                "habits": [
                    {
                        "habit_id": 1,
                        "start_time": "08:00:00",
                        "end_time": "09:00:00",
                        "day_config": "everyday"
                    },
                    {
                        "habit_id": 2,
                        "start_time": "21:30:00",
                        "end_time": "22:00:00",
                        "day_config": "weekdays"
                    }
                ]
            }
        }
    }

class PlanResponse(BaseModel):
    id: int
    name: str
    created_by: int
    is_public: bool
    difficulty: str
    habits_count: Optional[int] = None

    class Config:
        from_attributes = True
