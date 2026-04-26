from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, UniqueConstraint
from app.core.database import Base
from app.models.enums import HabitCategory

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(SQLEnum(HabitCategory), nullable=False)
    difficulty = Column(String, nullable=False) # e.g., easy, medium, hard
    base_score = Column(Integer, default=10, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("name", "created_by", name="uix_habit_name_creator"),
    )
