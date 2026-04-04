from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.core.database import Base
from app.models.enums import HabitCategory

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(SQLEnum(HabitCategory), nullable=False)
    difficulty = Column(String, nullable=False) # e.g., easy, medium, hard
    base_score = Column(Integer, default=10, nullable=False)
