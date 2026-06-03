import os
import sys
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup environment before importing app
TEST_DB_URL = "postgresql+asyncpg://lifeos:lifeos789@localhost:5432/lifeos"
os.environ["DATABASE_URL"] = TEST_DB_URL

# Import overrides (same as conftest.py to ensure standalone run matches environment)
import app.db
app.db.DATABASE_URL = TEST_DB_URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
app.db.engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={"server_settings": {"search_path": "test"}}
)
from sqlalchemy.orm import sessionmaker
app.db.AsyncSessionLocal = sessionmaker(
    bind=app.db.engine,
    class_=AsyncSession,
    expire_on_commit=False
)

import app.core.database as core_db
core_db.engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"server_settings": {"search_path": "test"}}
)
from sqlalchemy.ext.asyncio import async_sessionmaker
core_db.AsyncSessionLocal = async_sessionmaker(
    bind=core_db.engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

from app.main import app as fastapi_app
from app.models import Base
from tests.seed_data import seed_production_scale
from tests.generate_report import main as generate_reports
from sqlalchemy import text

async def run_seeding_and_simulation():
    """Initializes schemas and runs Phase 15 scale seeding."""
    print("Preparing test database...")
    default_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with default_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS test CASCADE;"))
        await conn.execute(text("CREATE SCHEMA test;"))
    await default_engine.dispose()
            
    # Create tables
    async with core_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Running production scale seeding simulation...")
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        await seed_production_scale(client)
        
    print("Seeding and simulation complete.")

def main():
    print("==================================================")
    print("      LifeOS AUTONOMOUS QA TEST SYSTEM            ")
    print("==================================================")
    
    # 1. Run Seeding and Simulation (Phase 15)
    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        loop.run_until_complete(run_seeding_and_simulation())
    finally:
        loop.close()
        
    # 2. Run Pytest suite programmatically to run specific scenario files
    print("\nRunning unit and concurrency tests...")
    pytest_args = ["-v", "tests/"]
    exit_code = pytest.main(pytest_args)
    print(f"Pytest run completed with exit code: {exit_code}")
    
    # 3. Generate Reports
    generate_reports()
    
    # 4. Cleanup temp results file and schema
    if os.path.exists("test_results_temp.json"):
        try:
            os.remove("test_results_temp.json")
        except OSError:
            pass

    print("Cleaning up test database schema...")
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        async def cleanup_schema():
            default_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
            async with default_engine.begin() as conn:
                await conn.execute(text("DROP SCHEMA IF EXISTS test CASCADE;"))
            await default_engine.dispose()
        loop.run_until_complete(cleanup_schema())
        loop.close()
    except Exception as e:
        print(f"Warning: Failed to drop test schema: {e}")
            
    print("\n==================================================")
    print("                  VERDICT                         ")
    print("==================================================")
    if exit_code == 0:
        print("SUCCESS: All tests passed, database verified!")
    else:
        print("FAILURE: Some tests failed, review coverage_report.md.")
        
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
