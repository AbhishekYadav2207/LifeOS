from fastapi import FastAPI
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.plans import router as plans_router
from app.api.execution import router as execution_router
from app.api.stats import router as stats_router

from app.models import Base
from app.models import *   # 🔥 THIS LINE IS REQUIRED

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="LifeOS V1 Backend Architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Welcome to LifeOS API"}