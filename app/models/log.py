from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Enum as SQLEnum
from app.core.database import Base
from app.models.enums import HabitCategory

class DailyLog(Base):
    __tablename__ = "daily_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="SET NULL"), nullable=True)
    
    # Snapshotted data for immutability and tracking
    snapshot_habit_name = Column(String, nullable=False)
    category = Column(SQLEnum(HabitCategory), nullable=False)
    snapshot_difficulty = Column(String, nullable=False)
    snapshot_base_score = Column(Integer, nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False) # pending, done, missed
    completion_timestamp = Column(DateTime(timezone=True), nullable=True)
    note = Column(String, nullable=True)
    late_flag = Column(Boolean, default=False)
    awarded_points = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'habit_id', 'date', name='uix_user_habit_date'),
    )

class DailySummary(Base):
    """Tracks idempotency for /process-day"""
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    total_score_change = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uix_user_date'),
    )
