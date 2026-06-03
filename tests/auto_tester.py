import os
import sys
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup environment before importing app
TEST_DB_URL = "sqlite+aiosqlite:///./test_lifeos.db"
os.environ["DATABASE_URL"] = TEST_DB_URL

# Import overrides (same as conftest.py to ensure standalone run matches environment)
import app.db
app.db.DATABASE_URL = TEST_DB_URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
app.db.engine = create_async_engine(TEST_DB_URL, echo=False, future=True, poolclass=NullPool)
from sqlalchemy.orm import sessionmaker
app.db.AsyncSessionLocal = sessionmaker(
    bind=app.db.engine,
    class_=AsyncSession,
    expire_on_commit=False
)

import app.core.database as core_db
core_db.engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
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

async def run_seeding_and_simulation():
    """Initializes schemas and runs Phase 15 scale seeding."""
    print("Preparing test database...")
    if os.path.exists("./test_lifeos.db"):
        try:
            os.remove("./test_lifeos.db")
        except OSError:
            pass
            
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
    
    # 4. Cleanup temp results file
    if os.path.exists("test_results_temp.json"):
        try:
            os.remove("test_results_temp.json")
        except OSError:
            pass
            
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
