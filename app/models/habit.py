from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, UniqueConstraint, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import HabitCategory


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(SQLEnum(HabitCategory), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=True)

    # Relationships
    profiles = relationship(
        "HabitProgressionProfile",
        back_populates="habit",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(HabitProgressionProfile.version)"
    )
    mastery_records = relationship(
        "HabitMastery",
        back_populates="habit",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("name", "created_by", name="uix_habit_name_creator"),
    )

    @property
    def active_profile(self) -> "HabitProgressionProfile":
        for p in self.profiles:
            if p.is_active:
                return p
        if self.profiles:
            return self.profiles[0]
        return None

    @property
    def difficulty(self) -> str:
        profile = self.active_profile
        if not profile:
            return "easy"
        coeff = profile.difficulty_coefficient
        if coeff < 2.5:
            return "easy"
        elif coeff < 4.0:
            return "medium"
        else:
            return "hard"

    @property
    def base_score(self) -> int:
        profile = self.active_profile
        if not profile:
            return 10
        return int(round(10 * profile.difficulty_coefficient))

    @property
    def estimated_duration_minutes(self) -> int:
        profile = self.active_profile
        return profile.estimated_duration_minutes if profile else 15

    @property
    def frequency(self) -> str:
        profile = self.active_profile
        return profile.frequency if profile else "daily"

    @property
    def habit_type(self) -> str:
        profile = self.active_profile
        return profile.habit_type if profile else "active"

    @property
    def difficulty_coefficient(self) -> float:
        profile = self.active_profile
        return profile.difficulty_coefficient if profile else 2.5

    @property
    def version(self) -> int:
        profile = self.active_profile
        return profile.version if profile else 1


class HabitProgressionProfile(Base):
    __tablename__ = "habit_progression_profiles"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    estimated_duration_minutes = Column(Integer, default=15, nullable=False)
    frequency = Column(String, default="daily", nullable=False)
    habit_type = Column(String, default="active", nullable=False)
    difficulty_coefficient = Column(Float, nullable=False)
    effective_from = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    habit = relationship("Habit", back_populates="profiles")

    __table_args__ = (
        UniqueConstraint("habit_id", "version", name="uix_habit_profile_version"),
    )


class HabitMastery(Base):
    __tablename__ = "habit_mastery"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="SET NULL"), nullable=True)
    times_completed = Column(Integer, default=0, nullable=False)
    total_time_spent = Column(Integer, default=0, nullable=False)  # in minutes
    mastery_xp = Column(Integer, default=0, nullable=False)
    mastery_level = Column(Integer, default=1, nullable=False)
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    habit = relationship("Habit", back_populates="mastery_records")

    __table_args__ = (
        UniqueConstraint("user_id", "habit_id", name="uix_user_habit_mastery"),
    )


class HabitDependency(Base):
    __tablename__ = "habit_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    child_habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    chain_order = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "parent_habit_id", "child_habit_id", name="uix_user_habit_chain"),
    )

