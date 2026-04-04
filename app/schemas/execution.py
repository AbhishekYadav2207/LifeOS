from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.enums import HabitCategory

class LogCompletionRequest(BaseModel):
    habit_id: int
    note: Optional[str] = None

class TodaysHabitResponse(BaseModel):
    id: int # log id
    habit_id: int
    name: str
    category: HabitCategory
    difficulty: str
    base_score: int
    status: str
    completion_timestamp: Optional[datetime] = None

class LogResponse(BaseModel):
    id: int
    habit_name: str
    category: HabitCategory
    status: str
    awarded_points: int
    late_flag: bool

    class Config:
        from_attributes = True
