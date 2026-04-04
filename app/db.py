from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./lifeos.db"

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

# Session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


# Dependency (for FastAPI routes)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session