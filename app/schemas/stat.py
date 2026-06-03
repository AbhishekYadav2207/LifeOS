from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserStatResponse(BaseModel):
    total_points: int
    total_score: int
    total_xp: int
    current_streak: int
    max_streak: int
    rank: str
    
    # Category Breakdowns
    focus_points: int
    health_points: int
    discipline_points: int
    mind_points: int

    # LifeOS v2 Progression Engine fields
    energy_score: int
    recovery_tokens: int
    prestige_level: int
    lifetime_xp: int
    consistency_7d: float
    consistency_30d: float
    consistency_90d: float

    class Config:
        from_attributes = True
