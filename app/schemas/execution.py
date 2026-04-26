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
    awarded_points: int = 0
    completion_timestamp: Optional[datetime] = None

class TodaySummary(BaseModel):
    """Live preview of today's progress — computed from current log state, not from process_day."""
    total_tasks: int
    completed: int
    pending: int
    missed: int
    earned_points: int
    possible_points: int
    completion_pct: float

class BackfillInfo(BaseModel):
    """Transparency about auto-processed missed days."""
    missed_days_processed: int
    remaining_unprocessed_days: int

class TodayResponse(BaseModel):
    """Full response for GET /today — tasks + live preview + backfill info."""
    tasks: List[TodaysHabitResponse]
    summary: TodaySummary
    backfill: BackfillInfo

class LogResponse(BaseModel):
    id: int
    habit_name: str
    category: HabitCategory
    status: str
    awarded_points: int
    late_flag: bool

    class Config:
        from_attributes = True
