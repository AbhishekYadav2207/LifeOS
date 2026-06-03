from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class ScoringVersion(Base):
    __tablename__ = "scoring_versions"

    id = Column(String, primary_key=True)  # e.g., "v1", "v2", "v3"
    description = Column(String, nullable=False)
    formula_name = Column(String, nullable=False)  # e.g., "dynamic_score_v2"
    formula_code = Column(String, nullable=True)   # Text of the python formula
    parameters = Column(JSON, nullable=False)      # Formula tuning parameters
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
