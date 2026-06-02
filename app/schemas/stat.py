from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserStatResponse(BaseModel):
    total_points: int
    total_score: int
    current_streak: int
    max_streak: int
    rank: str
    
    # Category Breakdowns
    focus_points: int
    health_points: int
    discipline_points: int
    mind_points: int

    class Config:
        from_attributes = True
