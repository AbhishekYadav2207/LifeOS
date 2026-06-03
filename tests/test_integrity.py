import pytest
from sqlalchemy import select, func
from app.models.user import User
from app.models.plan import UserPlan
from app.models.log import DailyLog
from app.models.stat import UserStat
from app.core.database import AsyncSessionLocal
from tests.seed_data import verify_db_integrity

@pytest.mark.asyncio
async def test_database_integrity_rules():
    # Execute the strict integrity verification function
    await verify_db_integrity()
    
    # Verify no duplicate active plans exist for any user
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User.id))).scalars().all()
        for u_id in users:
            active_plans_q = select(func.count(UserPlan.id)).where(
                UserPlan.user_id == u_id,
                UserPlan.active == True
            )
            count = (await session.execute(active_plans_q)).scalar() or 0
            assert count <= 1, f"User {u_id} has {count} active plans!"
