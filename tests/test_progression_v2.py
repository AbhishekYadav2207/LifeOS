import pytest
from httpx import AsyncClient
import datetime
from sqlalchemy import select
from app.models.stat import UserStat, ProgressionEvent, UserMilestone, CategoryProgression
from app.models.habit import HabitDependency, HabitMastery, Habit
from app.models.scoring_version import ScoringVersion
from app.models.log import DailyLog
from app.models.plan import PlanHabit, UserPlan
from app.core.database import AsyncSessionLocal
from app.models.enums import HabitCategory

@pytest.fixture(autouse=True)
async def seed_v2_scoring(db_session):
    # Seed V2 scoring version as active
    v2 = ScoringVersion(
        id="v2",
        description="Redesigned Progression Engine",
        formula_name="progression_v2",
        parameters={"energy_decay": -5, "perfect_day_bonus": 10},
        is_active=True
    )
    db_session.add(v2)
    await db_session.commit()

@pytest.mark.asyncio
async def test_habit_difficulty_coefficients(client: AsyncClient, mock_time):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "diff_user@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "diff_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a habit with specific duration, frequency, type (V2 payload)
    h_resp = await client.post("/api/v1/plans/habits", json={
        "name": "Hard Active Gym Session",
        "category": "health",
        "estimated_duration_minutes": 100,  # DurationWeight = 2.5
        "frequency": "weekends",             # FrequencyWeight = 1.5
        "habit_type": "active",             # TypeWeight = 1.5
    }, headers=headers)
    assert h_resp.status_code == 200
    h_data = h_resp.json()["data"]
    
    # Coeff = 2.5 + 1.5 + 1.5 = 5.5. Base score = round(10 * 5.5) = 55.
    assert h_data["difficulty_coefficient"] == 5.5
    assert h_data["base_score"] == 55
    assert h_data["estimated_duration_minutes"] == 100
    assert h_data["frequency"] == "weekends"
    assert h_data["habit_type"] == "active"


@pytest.mark.asyncio
async def test_v2_habit_completion_and_snapshots(client: AsyncClient, mock_time, db_session):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "v2_comp@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "v2_comp@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create habit (coeff = 1.0 + 1.0 + 1.5 = 3.5. Base = 35)
    h_id = (await client.post("/api/v1/plans/habits", json={
        "name": "V2 Habit",
        "category": "focus",
        "estimated_duration_minutes": 15,
        "frequency": "daily",
        "habit_type": "active"
    }, headers=headers)).json()["data"]["id"]

    # Create Plan
    plan_resp = await client.post("/api/v1/plans/", json={
        "name": "V2 Plan",
        "difficulty": "easy",
        "habits": [
            {"habit_id": h_id, "start_time": "08:00:00", "end_time": "10:00:00", "day_config": "everyday"}
        ]
    }, headers=headers)
    p_id = plan_resp.json()["data"]["id"]

    # Activate
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)

    # Initialize logs (should capture snapshots)
    await client.get("/api/v1/execution/today", headers=headers)

    # Fetch log from DB to inspect snapshots
    async with AsyncSessionLocal() as session:
        log_db = (await session.execute(select(DailyLog).where(DailyLog.habit_id == h_id))).scalars().first()
        assert log_db is not None
        assert log_db.profile_snapshot_json is not None
        assert log_db.profile_snapshot_json["difficulty"] == 3.5
        assert log_db.profile_snapshot_json["frequency"] == "daily"
        assert log_db.formula_snapshot_json is not None
        assert log_db.formula_snapshot_json["formula_name"] == "progression_v2"

    # Complete on-time (9:15 is before end_time 10:00)
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 15, 0, tzinfo=datetime.timezone.utc))
    comp_resp = await client.post("/api/v1/execution/habit/complete", json={"habit_id": h_id}, headers=headers)
    assert comp_resp.status_code == 200

    # Verify score events and total XP are updated in UserStat
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        # Base XP = 35. Quality mult = 1.0 (on-time). Consistency mult = 1.2 (default perfect). Mastery bonus = 0.
        # Energy score default = 100 -> mult = 0.9 + 0.2 * 1.0 = 1.1.
        # Gained XP = round(35 * 1.0 * 1.2 * 1.1) = 46.
        assert stat_db.total_xp == 46
        assert stat_db.lifetime_xp == 46
        assert stat_db.energy_score == 100 # capped at 100 (+5 from completion)


@pytest.mark.asyncio
async def test_dynamic_daily_xp_cap(client: AsyncClient, mock_time, db_session):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "cap_user@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "cap_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set user rank level to 2 (Starter). Starter daily cap = 500 + 2 * 100 = 700.
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        stat_db.rank = "Starter"
        stat_db.total_xp = 2000
        stat_db.lifetime_xp = 2000
        await session.commit()

    # Create very high base score habits
    h1 = (await client.post("/api/v1/plans/habits", json={
        "name": "Epic Gym Session", "category": "health",
        "estimated_duration_minutes": 120, "frequency": "custom", "habit_type": "active"
    }, headers=headers)).json()["data"]["id"]

    h2 = (await client.post("/api/v1/plans/habits", json={
        "name": "Additional Habit", "category": "focus",
        "estimated_duration_minutes": 15, "frequency": "daily", "habit_type": "active"
    }, headers=headers)).json()["data"]["id"]

    plan_resp = await client.post("/api/v1/plans/", json={
        "name": "Epic Plan",
        "difficulty": "hard",
        "habits": [
            {"habit_id": h1, "day_config": "everyday"},
            {"habit_id": h2, "day_config": "everyday"}
        ]
    }, headers=headers)
    p_id = plan_resp.json()["data"]["id"]

    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)

    # Initialize logs
    await client.get("/api/v1/execution/today", headers=headers)

    # Fake award points to reach near cap (680 XP already earned today)
    async with AsyncSessionLocal() as session:
        log_db = (await session.execute(select(DailyLog).where(DailyLog.habit_id == h1))).scalars().first()
        # Create a dummy done log with 680 points
        log_db.status = "done"
        log_db.awarded_points = 680
        await session.commit()

    # Complete h2. Base score coeff = 2.5 + 1.0 + 1.5 = 5.0. Base XP = 50. Energy mult = 1.1.
    # Total gained would be 55. But cap is 700. 680 already earned. Max allowed is 20.
    comp_resp = await client.post("/api/v1/execution/habit/complete", json={"habit_id": h2}, headers=headers)
    assert comp_resp.status_code == 200
    assert comp_resp.json()["data"]["awarded_points"] == 20


@pytest.mark.asyncio
async def test_recovery_token_source(client: AsyncClient, mock_time, db_session):
    # Register and login
    await client.post("/api/v1/auth/register", json={"email": "token_source@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "token_source@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set user stats to 6 perfect days streak, recovery_tokens = 0
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        stat_db.current_streak = 6
        stat_db.recovery_tokens = 0
        await session.commit()

    # Create habit
    h_id = (await client.post("/api/v1/plans/habits", json={"name": "Daily Habit", "category": "focus", "estimated_duration_minutes": 15}, headers=headers)).json()["data"]["id"]
    p_id = (await client.post("/api/v1/plans/", json={
        "name": "Plan", "difficulty": "easy", "habits": [{"habit_id": h_id}]
    }, headers=headers)).json()["data"]["id"]

    # Day 7 completion
    mock_time.set_time(datetime.datetime(2026, 6, 7, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)
    await client.get("/api/v1/execution/today", headers=headers)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": h_id}, headers=headers)

    # Process day -> yields 7th streak day -> perfect day -> should award +1 token
    # Also 30d consistency > 95% awards +1 token, making total 2 tokens
    pd = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd.status_code == 200
    assert pd.json()["data"]["streak"] == 7

    # Check recovery tokens
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        assert stat_db.recovery_tokens == 2


@pytest.mark.asyncio
async def test_burnout_detection_event(client: AsyncClient, mock_time, db_session):
    # Register and login
    await client.post("/api/v1/auth/register", json={"email": "burnout@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "burnout@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create 16 habits to trigger burnout threshold (>15 habits)
    habits = []
    for i in range(16):
        h = (await client.post("/api/v1/plans/habits", json={"name": f"Habit {i}", "category": "focus", "estimated_duration_minutes": 15}, headers=headers)).json()["data"]["id"]
        habits.append({"habit_id": h, "day_config": "everyday"})

    # Create and activate plan
    p_id = (await client.post("/api/v1/plans/", json={"name": "Heavy Plan", "difficulty": "hard", "habits": habits}, headers=headers)).json()["data"]["id"]
    
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)

    # Day 1: Process day with 0 completed tasks (completion rate 0% < 40%)
    await client.get("/api/v1/execution/today", headers=headers)
    pd = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd.status_code == 200

    # Verify that a burnout event was emitted in progression_events
    async with AsyncSessionLocal() as session:
        evts = (await session.execute(select(ProgressionEvent).where(ProgressionEvent.event_type == "burnout_detected"))).scalars().all()
        assert len(evts) == 1
        assert evts[0].payload["active_habits_count"] == 16
        assert "potential burnout" in evts[0].payload["suggestion"]


@pytest.mark.asyncio
async def test_prestige_system(client: AsyncClient, mock_time, db_session):
    # Register and login
    await client.post("/api/v1/auth/register", json={"email": "prestige_user@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "prestige_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set user stats to Transcendent rank boundary (rank_score >= 400000)
    # Let's seed category progressions and high mastery levels
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        stat_db.rank = "Transcendent"
        stat_db.total_xp = 800000
        stat_db.lifetime_xp = 800000
        stat_db.focus_points = 200000
        stat_db.health_points = 200000
        stat_db.discipline_points = 200000
        stat_db.mind_points = 200000

        # Category Progressions
        for cat in [HabitCategory.focus, HabitCategory.health, HabitCategory.discipline, HabitCategory.mind]:
            session.add(CategoryProgression(user_id=stat_db.user_id, category=cat, category_xp=200000, category_level=42))
        
        # Mastery record (must not reset)
        session.add(HabitMastery(user_id=stat_db.user_id, habit_id=None, times_completed=500, total_time_spent=7500, mastery_xp=5000, mastery_level=12))
        
        await session.commit()

    # Call prestige endpoint
    prest_resp = await client.post("/api/v1/stats/prestige", headers=headers)
    assert prest_resp.status_code == 200
    p_data = prest_resp.json()["data"]
    assert p_data["prestige_level"] == 1
    assert p_data["rank"] == "Beginner"
    assert p_data["total_xp"] == 0
    assert p_data["lifetime_xp"] == 800000  # Preserved!

    # Check database preservation
    async with AsyncSessionLocal() as session:
        stat_db = (await session.execute(select(UserStat))).scalars().first()
        assert stat_db.focus_points == 0
        assert stat_db.health_points == 0
        assert stat_db.prestige_level == 1
        
        # Category progressions reset
        cat_progs = (await session.execute(select(CategoryProgression))).scalars().all()
        for cp in cat_progs:
            assert cp.category_xp == 0
            assert cp.category_level == 1

        # Mastery record preserved
        mastery = (await session.execute(select(HabitMastery))).scalars().all()
        assert len(mastery) == 1
        assert mastery[0].mastery_level == 12
        assert mastery[0].times_completed == 500

        # Milestone recorded
        milestones = (await session.execute(select(UserMilestone).where(UserMilestone.milestone_type == "prestige_reached"))).scalars().all()
        assert len(milestones) == 1
        assert milestones[0].value == 1


@pytest.mark.asyncio
async def test_habit_dependency_cycles(client: AsyncClient, mock_time, db_session):
    # Register and login
    await client.post("/api/v1/auth/register", json={"email": "cycles@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "cycles@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create habits A, B, C
    a_id = (await client.post("/api/v1/plans/habits", json={"name": "A", "category": "focus"}, headers=headers)).json()["data"]["id"]
    b_id = (await client.post("/api/v1/plans/habits", json={"name": "B", "category": "focus"}, headers=headers)).json()["data"]["id"]
    c_id = (await client.post("/api/v1/plans/habits", json={"name": "C", "category": "focus"}, headers=headers)).json()["data"]["id"]

    # Link A -> B
    r1 = await client.post("/api/v1/plans/habits/dependencies", json={"parent_habit_id": a_id, "child_habit_id": b_id}, headers=headers)
    assert r1.status_code == 200

    # Link B -> C
    r2 = await client.post("/api/v1/plans/habits/dependencies", json={"parent_habit_id": b_id, "child_habit_id": c_id}, headers=headers)
    assert r2.status_code == 200

    # Try Link C -> A (should fail: cyclic dependency)
    r3 = await client.post("/api/v1/plans/habits/dependencies", json={"parent_habit_id": c_id, "child_habit_id": a_id}, headers=headers)
    assert r3.status_code == 400
    assert "Cyclic dependencies are not allowed" in r3.json()["detail"]

    # Try Link A -> A (should fail: self-loop)
    r4 = await client.post("/api/v1/plans/habits/dependencies", json={"parent_habit_id": a_id, "child_habit_id": a_id}, headers=headers)
    assert r4.status_code == 400
    assert "self-loop detected" in r4.json()["detail"]
