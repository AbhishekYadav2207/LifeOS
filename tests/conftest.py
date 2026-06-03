import os
import sys
import pytest
import asyncio
import datetime
import json
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# 1. Override database URL and engine before any other imports
TEST_DB_URL = "postgresql+asyncpg://lifeos:lifeos789@localhost:5432/lifeos"
os.environ["DATABASE_URL"] = TEST_DB_URL

# Import app.db and override (using NullPool to avoid event loop bindings)
import app.db
app.db.DATABASE_URL = TEST_DB_URL
app.db.engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={"server_settings": {"search_path": "test"}}
)
app.db.AsyncSessionLocal = sessionmaker(
    bind=app.db.engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Import app.core.database and override (using NullPool to avoid event loop bindings)
import app.core.database as core_db
core_db.engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"server_settings": {"search_path": "test"}}
)
core_db.AsyncSessionLocal = async_sessionmaker(
    bind=core_db.engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

from app.main import app
from app.models import Base
from app.core.database import get_db
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

@pytest.fixture(autouse=True)
async def setup_db():
    # Connect to default schema/database to create test schema
    default_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with default_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS test CASCADE;"))
        await conn.execute(text("CREATE SCHEMA test;"))
    await default_engine.dispose()
        
    # Create tables
    async with core_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    
    # Cleanup after test
    default_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with default_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS test CASCADE;"))
    await default_engine.dispose()

@pytest.fixture
async def db_session():
    async with core_db.AsyncSessionLocal() as session:
        yield session

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

class MockTimeProvider:
    def __init__(self):
        # Base date is 2026-06-01 08:00:00 UTC (a Monday)
        self.current_dt = datetime.datetime(2026, 6, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
        
    def set_time(self, dt: datetime.datetime):
        self.current_dt = dt
        
    def shift_days(self, days: int):
        self.current_dt += datetime.timedelta(days=days)
        
    def shift_hours(self, hours: int):
        self.current_dt += datetime.timedelta(hours=hours)

@pytest.fixture
def mock_time():
    provider = MockTimeProvider()
    
    def get_mocked_time(tz_name="UTC"):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        return provider.current_dt.astimezone(tz)
        
    # We patch the imported get_current_time in all the services and core.time
    with patch("app.services.scoring_svc.get_current_time", side_effect=get_mocked_time), \
         patch("app.services.execution_svc.get_current_time", side_effect=get_mocked_time), \
         patch("app.services.plan_svc.get_current_time", side_effect=get_mocked_time), \
         patch("app.core.time.get_current_time", side_effect=get_mocked_time), \
         patch("app.core.time.get_local_today", side_effect=lambda tz="UTC": get_mocked_time(tz).date()):
        yield provider

# Pytest hooks for programmatically logging results
test_results = []

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        test_results.append({
            "nodeid": rep.nodeid,
            "outcome": rep.outcome,
            "duration": rep.duration,
            "error": str(rep.longrepr) if rep.longrepr else None
        })

def pytest_sessionfinish(session, exitstatus):
    with open("test_results_temp.json", "w") as f:
        json.dump(test_results, f, indent=2)
