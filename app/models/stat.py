from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, CheckConstraint, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import HabitCategory

class UserStat(Base):
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False, index=True)
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)
    
    @property
    def total_points(self):
        return self.total_xp

    @total_points.setter
    def total_points(self, value):
        self.total_xp = value
    
    # Category splits (backward compatible)
    focus_points = Column(Integer, default=0, nullable=False)
    health_points = Column(Integer, default=0, nullable=False)
    discipline_points = Column(Integer, default=0, nullable=False)
    mind_points = Column(Integer, default=0, nullable=False)

    # LifeOS v2 Progression Engine fields
    energy_score = Column(Integer, default=100, nullable=False)
    recovery_tokens = Column(Integer, default=1, nullable=False)
    prestige_level = Column(Integer, default=0, nullable=False)
    lifetime_xp = Column(Integer, default=0, nullable=False, index=True)
    rank = Column(String, default="Beginner", nullable=False, index=True)
    consistency_7d = Column(Float, default=0.0, nullable=False)
    consistency_30d = Column(Float, default=0.0, nullable=False)
    consistency_90d = Column(Float, default=0.0, nullable=False)

    __table_args__ = (
        CheckConstraint("recovery_tokens >= 0", name="check_recovery_tokens_min"),
        CheckConstraint("recovery_tokens <= 3", name="check_recovery_tokens_max"),
        CheckConstraint("energy_score >= 0", name="check_energy_score_min"),
        CheckConstraint("energy_score <= 100", name="check_energy_score_max"),
        CheckConstraint("consistency_7d >= 0.0", name="check_consistency_7d_min"),
        CheckConstraint("consistency_7d <= 1.0", name="check_consistency_7d_max"),
        CheckConstraint("consistency_30d >= 0.0", name="check_consistency_30d_min"),
        CheckConstraint("consistency_30d <= 1.0", name="check_consistency_30d_max"),
        CheckConstraint("consistency_90d >= 0.0", name="check_consistency_90d_min"),
        CheckConstraint("consistency_90d <= 1.0", name="check_consistency_90d_max"),
        CheckConstraint("total_xp >= 0", name="check_total_xp_min"),
        CheckConstraint("lifetime_xp >= 0", name="check_lifetime_xp_min"),
    )


class UserPlanStat(Base):
    __tablename__ = "user_plan_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)
    
    @property
    def total_points(self):
        return self.total_xp

    @total_points.setter
    def total_points(self, value):
        self.total_xp = value
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)

    # Category splits
    focus_points = Column(Integer, default=0, nullable=False)
    health_points = Column(Integer, default=0, nullable=False)
    discipline_points = Column(Integer, default=0, nullable=False)
    mind_points = Column(Integer, default=0, nullable=False)


class ScoreEvent(Base):
    __tablename__ = "score_events"

    event_id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # habit_completed, perfect_day_bonus, admin_adjustment
    old_xp = Column(Integer, nullable=False)
    delta_xp = Column(Integer, nullable=False)
    new_xp = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_score_events_user_id_date', 'user_id', 'date'),
        Index('ix_score_events_event_type', 'event_type'),
        Index('ix_score_events_created_at', 'created_at'),
    )


class CategoryProgression(Base):
    __tablename__ = "category_progressions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(SQLEnum(HabitCategory), nullable=False)
    category_xp = Column(Integer, default=0, nullable=False)
    category_level = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uix_user_category_progression"),
        Index("ix_category_progressions_user_category", "user_id", "category"),
    )


class SystemJob(Base):
    __tablename__ = "system_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, unique=True, nullable=False)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, running, completed, failed


class UserMilestone(Base):
    __tablename__ = "user_milestones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_type = Column(String, nullable=False)  # xp_reached, streak_reached, prestige_reached, completions_reached
    value = Column(Integer, nullable=False)
    achieved_at = Column(DateTime(timezone=True), server_default=func.now())


class ProgressionEvent(Base):
    __tablename__ = "progression_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_progression_events_created_at', 'created_at'),
    )

@event.listens_for(ScoreEvent, "before_update")
def prevent_score_event_update(mapper, connection, target):
    raise ValueError("ScoreEvent records are immutable and cannot be updated.")

@event.listens_for(ScoreEvent, "before_delete")
def prevent_score_event_delete(mapper, connection, target):
    raise ValueError("ScoreEvent records are immutable and cannot be deleted.")

@event.listens_for(ProgressionEvent, "before_update")
def prevent_progression_event_update(mapper, connection, target):
    raise ValueError("ProgressionEvent records are immutable and cannot be updated.")

@event.listens_for(ProgressionEvent, "before_delete")
def prevent_progression_event_delete(mapper, connection, target):
    raise ValueError("ProgressionEvent records are immutable and cannot be deleted.")
