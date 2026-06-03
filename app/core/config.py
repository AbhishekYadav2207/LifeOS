import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "LifeOS V1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://lifeos:lifeos789@localhost:5432/lifeos")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
settings = Settings()
print("DATABASE_URL =", settings.DATABASE_URL)