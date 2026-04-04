from sqlalchemy import Column, Integer, ForeignKey
from app.core.database import Base

class UserStat(Base):
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)
    
    # Category splits
    focus_points = Column(Integer, default=0, nullable=False)
    health_points = Column(Integer, default=0, nullable=False)
    discipline_points = Column(Integer, default=0, nullable=False)
    mind_points = Column(Integer, default=0, nullable=False)

class UserPlanStat(Base):
    __tablename__ = "user_plan_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)

    focus_points = Column(Integer, default=0, nullable=False)
    health_points = Column(Integer, default=0, nullable=False)
    discipline_points = Column(Integer, default=0, nullable=False)
    mind_points = Column(Integer, default=0, nullable=False)
