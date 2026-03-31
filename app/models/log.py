from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey
from app.core.database import Base

class DailyLog(Base):
    __tablename__ = "daily_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="SET NULL"), nullable=True) # Could be null if habit deleted
    
    # Snapshotted data for immutability
    snapshot_habit_name = Column(String, nullable=False)
    snapshot_category = Column(String, nullable=False)
    snapshot_difficulty = Column(String, nullable=False)
    snapshot_base_score = Column(Integer, nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False) # pending, done, missed
    completion_timestamp = Column(DateTime(timezone=True), nullable=True)
    note = Column(String, nullable=True)
    late_flag = Column(Boolean, default=False)
    points_awarded = Column(Integer, default=0, nullable=False)
