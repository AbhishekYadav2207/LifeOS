from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.core.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for preset plans
    is_public = Column(Boolean, default=False)
    difficulty = Column(String, nullable=False)

class PlanHabit(Base):
    __tablename__ = "plan_habits"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    time_window = Column(String) # e.g., "morning", "evening", "anytime"
    day_config = Column(String, default="everyday") # e.g., "everyday", "weekdays", "weekends"

class UserPlan(Base):
    __tablename__ = "user_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    active = Column(Boolean, default=True)
    start_date = Column(Date, nullable=False)
