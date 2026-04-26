from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from app.core.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    difficulty = Column(String, nullable=False)

    # Relationships
    plan_habits = relationship("PlanHabit", back_populates="plan", cascade="all, delete-orphan")

class PlanHabit(Base):
    __tablename__ = "plan_habits"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Time, nullable=True) # E.g., 08:00:00. Optional based on plan mapping
    end_time = Column(Time, nullable=True)   # E.g., 20:00:00 bounds for lateness logic
    day_config = Column(String, default="everyday")

    # Relationships
    plan = relationship("Plan", back_populates="plan_habits")
    habit = relationship("Habit")

class UserPlan(Base):
    __tablename__ = "user_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    active = Column(Boolean, default=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
