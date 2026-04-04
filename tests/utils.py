from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.habit import Habit
from app.models.plan import Plan, PlanHabit
from app.models.stat import UserStat
from app.models.enums import HabitCategory
from app.core.security import get_password_hash
from datetime import time

async def create_test_user(db: AsyncSession, email="test@example.com", password="password"):
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        timezone="UTC"
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    user_stat = UserStat(user_id=user.id)
    db.add(user_stat)
    await db.commit()
    await db.refresh(user)
    return user

async def create_test_habit(db: AsyncSession, name="Test Habit", category=HabitCategory.focus, difficulty="easy", base_score=10):
    habit = Habit(name=name, category=category, difficulty=difficulty, base_score=base_score)
    db.add(habit)
    await db.commit()
    await db.refresh(habit)
    return habit

async def create_test_plan(db: AsyncSession, creator_id: int, habits: list = None):
    plan = Plan(name="Test Plan", created_by=creator_id, is_public=True, difficulty="easy")
    db.add(plan)
    await db.flush()
    await db.refresh(plan)

    if habits:
        for item in habits:
            ph = PlanHabit(
                plan_id=plan.id,
                habit_id=item["habit"].id,
                start_time=item.get("start_time", time(8, 0)),
                end_time=item.get("end_time", time(20, 0)),
                day_config="everyday"
            )
            db.add(ph)
    await db.commit()
    await db.refresh(plan)
    return plan
