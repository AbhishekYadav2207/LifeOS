import pytest
from datetime import datetime, timedelta, date, timezone
from app.models.enums import HabitCategory
from app.models.plan import UserPlan
from app.models.log import DailyLog
from app.services import execution_svc, scoring_svc
from tests.utils import create_test_user, create_test_habit, create_test_plan
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_multi_day_stateful_simulation(db_session):
    """
    Day 1 -> Full
    Day 2 -> Partial
    Day 3 -> Late (All done but late = streak increases)
    Day 4 -> Full
    """
    user = await create_test_user(db_session, email="stateful@test.com")
    habit1 = await create_test_habit(db_session, name="S1", category=HabitCategory.discipline, base_score=20)
    habit2 = await create_test_habit(db_session, name="S2", category=HabitCategory.health, base_score=20)
    
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[
        {"habit": habit1}, {"habit": habit2}
    ])
    
    # Helper to simulate a day
    async def simulate_day(sim_date: date, completes: list, late: bool = False):
        up = await db_session.execute(select(UserPlan).where(UserPlan.user_id == user.id))
        if not up.scalars().first():
            new_up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=sim_date)
            db_session.add(new_up)
            await db_session.commit()
            
        logs = await execution_svc.initialize_logs_for_today(db_session, user, sim_date)
        for log in logs:
            if log.habit_id in completes:
                log.status = "done"
                log.late_flag = late
        await db_session.commit()
        return await scoring_svc.process_day(db_session, user, sim_date)
        
    base_date = date(2025, 1, 1)
    
    # Day 1: Full
    r1 = await simulate_day(base_date, [habit1.id, habit2.id])
    assert r1["streak"] == 1
    assert r1["score_change"] == 40
    
    # Day 2: Partial
    r2 = await simulate_day(base_date + timedelta(days=1), [habit1.id])
    assert r2["streak"] == 0 # Reset
    assert r2["score_change"] == 10 # 20 (H1) - 10 (H2 missed)
    
    # Day 3: Late
    r3 = await simulate_day(base_date + timedelta(days=2), [habit1.id, habit2.id], late=True)
    assert r3["streak"] == 1 # Recovers!
    assert r3["score_change"] == 20 # Late = 10 + 10
    
    # Day 4: Full
    r4 = await simulate_day(base_date + timedelta(days=3), [habit1.id, habit2.id])
    assert r4["streak"] == 2
    assert r4["score_change"] == 40
    
    assert r4["new_total"] == 40 + 10 + 20 + 40 # 110
