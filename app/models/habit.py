from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False) # e.g., focus, health, discipline, mind
    difficulty = Column(String, nullable=False) # e.g., easy, medium, hard
    base_score = Column(Integer, default=10, nullable=False)
