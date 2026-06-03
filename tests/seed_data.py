import os
import sys
import random
import datetime
import json
from zoneinfo import ZoneInfo
from unittest.mock import patch
from sqlalchemy import select, func

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.enums import HabitCategory
from app.models.user import User
from app.models.habit import Habit
from app.models.plan import Plan, PlanHabit, UserPlan
from app.models.log import DailyLog, DailySummary
from app.models.stat import UserStat, UserPlanStat
from app.core.database import AsyncSessionLocal
from faker import Faker

fake = Faker()

class GlobalMockTime:
    def __init__(self):
        # Base date is 2026-06-01 08:00:00 UTC (a Monday)
        self.current_dt = datetime.datetime(2026, 6, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    
    def set_time(self, dt: datetime.datetime):
        self.current_dt = dt
        
    def shift_days(self, days: int):
        self.current_dt += datetime.timedelta(days=days)
        
    def get_current_time(self, tz_name="UTC"):
        tz = ZoneInfo(tz_name)
        return self.current_dt.astimezone(tz)
        
    def get_local_today(self, tz_name="UTC"):
        return self.get_current_time(tz_name).date()

mock_time_provider = GlobalMockTime()

class TimeMocker:
    def __enter__(self):
        self.patchers = [
            patch("app.services.scoring_svc.get_current_time", side_effect=mock_time_provider.get_current_time),
            patch("app.services.execution_svc.get_current_time", side_effect=mock_time_provider.get_current_time),
            patch("app.services.plan_svc.get_current_time", side_effect=mock_time_provider.get_current_time),
            patch("app.core.time.get_current_time", side_effect=mock_time_provider.get_current_time),
            patch("app.core.time.get_local_today", side_effect=lambda tz="UTC": mock_time_provider.get_current_time(tz).date())
        ]
        for p in self.patchers:
            p.start()
        return mock_time_provider
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in self.patchers:
            p.stop()

# Helper function to execute daily processing, handle completion logic, and assert database integrity.
async def run_simulation(client, users, habit_ids, plan_ids, days=14):
    """
    Runs a simulation for 'days' days.
    For each day:
      - 70% completed habits
      - 10% completed late habits
      - 20% missed habits
    Runs daily processing.
    Verifies database integrity after every step.
    """
    print(f"Starting {days}-day simulation...")
    
    with TimeMocker() as time_prov:
        for day_idx in range(days):
            current_date = time_prov.get_local_today("UTC")
            print(f"--- Simulating Day {day_idx + 1}: {current_date} ---")
            
            # Step 1: For each user, retrieve today's tasks to initialize logs.
            for u in users:
                headers = {"Authorization": f"Bearer {u['token']}"}
                
                # Fetch today's tasks (which auto-initializes the logs)
                today_resp = await client.get("/api/v1/execution/today", headers=headers)
                if today_resp.status_code != 200:
                    print(f"Warning: Failed to fetch /today for User {u['email']}: {today_resp.text}")
                    continue
                    
                tasks = today_resp.json().get("data", [])
                if not tasks:
                    continue
                    
                # Distribute completion: 70% completed, 10% late, 20% missed
                random.shuffle(tasks)
                num_tasks = len(tasks)
                num_done = int(num_tasks * 0.7)
                num_late = int(num_tasks * 0.1)
                
                # Complete the 70% done tasks (on time)
                # We mock current time to be within bounds (e.g. 10:00 AM)
                time_prov.set_time(datetime.datetime(2026, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=day_idx))
                
                for task in tasks[:num_done]:
                    comp_resp = await client.post("/api/v1/execution/habit/complete", json={
                        "habit_id": task["habit_id"],
                        "note": f"Done on day {day_idx + 1}"
                    }, headers=headers)
                    if comp_resp.status_code != 200:
                        print(f"Warning: Failed to complete task {task['name']}: {comp_resp.text}")
                        
                # Complete the 10% late tasks
                # We mock current time to be late (e.g. 23:30 PM)
                time_prov.set_time(datetime.datetime(2026, 6, 1, 23, 30, 0, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=day_idx))
                
                for task in tasks[num_done:num_done+num_late]:
                    comp_resp = await client.post("/api/v1/execution/habit/complete", json={
                        "habit_id": task["habit_id"],
                        "note": f"Done late on day {day_idx + 1}"
                    }, headers=headers)
                    if comp_resp.status_code != 200:
                        print(f"Warning: Failed to complete task late {task['name']}: {comp_resp.text}")
                        
                # 20% missed (we do nothing, they remain pending and will be swept on process-day)
                
            # Step 2: Run daily processing for each user
            time_prov.set_time(datetime.datetime(2026, 6, 1, 23, 59, 0, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=day_idx))
            for u in users:
                headers = {"Authorization": f"Bearer {u['token']}"}
                pd_resp = await client.post("/api/v1/stats/process-day", headers=headers)
                if pd_resp.status_code != 200:
                    print(f"Warning: Failed to process day for User {u['email']}: {pd_resp.text}")
                    
            # Step 3: Run Database Integrity Checks
            await verify_db_integrity()
            
            # Step 4: Shift mock time to the next day
            time_prov.set_time(datetime.datetime(2026, 6, 1, 8, 0, 0, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=day_idx + 1))
            
    print("Simulation complete!")

async def verify_db_integrity():
    """Verify foreign keys, check for orphans, and ensure stats are consistent with execution history."""
    async with AsyncSessionLocal() as session:
        # Check for orphan records
        # DailyLog with missing User
        orphan_logs_q = select(DailyLog).where(~DailyLog.user_id.in_(select(User.id)))
        orphan_logs = (await session.execute(orphan_logs_q)).scalars().all()
        assert len(orphan_logs) == 0, f"Found {len(orphan_logs)} orphan DailyLog records!"
        
        # UserPlan with missing User
        orphan_user_plans_q = select(UserPlan).where(~UserPlan.user_id.in_(select(User.id)))
        orphan_user_plans = (await session.execute(orphan_user_plans_q)).scalars().all()
        assert len(orphan_user_plans) == 0, f"Found {len(orphan_user_plans)} orphan UserPlan records!"
        
        # UserStat with missing User
        orphan_user_stats_q = select(UserStat).where(~UserStat.user_id.in_(select(User.id)))
        orphan_user_stats = (await session.execute(orphan_user_stats_q)).scalars().all()
        assert len(orphan_user_stats) == 0, f"Found {len(orphan_user_stats)} orphan UserStat records!"

        # Verify UserStat matches historical daily updates (processed day-by-day to respect max(0, ...) floors)
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        for user in users:
            stat_q = select(UserStat).where(UserStat.user_id == user.id)
            user_stat = (await session.execute(stat_q)).scalars().first()
            if not user_stat:
                continue
                
            # Get all summaries for this user, sorted by date
            summaries_q = select(DailySummary).where(DailySummary.user_id == user.id).order_by(DailySummary.date)
            summaries = (await session.execute(summaries_q)).scalars().all()
            
            expected_total = 0
            expected_cats = {cat: 0 for cat in HabitCategory}
            
            for summary in summaries:
                # Get all logs for this date
                logs_q = select(DailyLog).where(DailyLog.user_id == user.id, DailyLog.date == summary.date)
                logs = (await session.execute(logs_q)).scalars().all()
                
                day_total = 0
                day_cats = {cat: 0 for cat in HabitCategory}
                
                for log in logs:
                    day_total += log.awarded_points
                    day_cats[log.category] += log.awarded_points
                    
                expected_total = max(0, expected_total + day_total)
                for cat in HabitCategory:
                    expected_cats[cat] = max(0, expected_cats[cat] + day_cats[cat])
                    
            # Check total points
            assert user_stat.total_points == expected_total, (
                f"Total points mismatch for User {user.id}! "
                f"Expected: {expected_total}, Got: {user_stat.total_points}"
            )
            
            # Check categories
            for cat in HabitCategory:
                db_cat_points = getattr(user_stat, f"{cat.value}_points")
                assert db_cat_points == expected_cats[cat], (
                    f"Category {cat.value} points mismatch for User {user.id}! "
                    f"Expected: {expected_cats[cat]}, Got: {db_cat_points}"
                )

async def generate_database_snapshot(output_path="database_snapshot.json"):
    """Generates counts for all database tables and outputs them as JSON."""
    async with AsyncSessionLocal() as session:
        users_count = (await session.execute(select(func.count(User.id)))).scalar()
        habits_count = (await session.execute(select(func.count(Habit.id)))).scalar()
        plans_count = (await session.execute(select(func.count(Plan.id)))).scalar()
        plan_habits_count = (await session.execute(select(func.count(PlanHabit.id)))).scalar()
        user_plans_count = (await session.execute(select(func.count(UserPlan.id)))).scalar()
        daily_logs_count = (await session.execute(select(func.count(DailyLog.id)))).scalar()
        daily_summaries_count = (await session.execute(select(func.count(DailySummary.id)))).scalar()
        user_stats_count = (await session.execute(select(func.count(UserStat.id)))).scalar()
        user_plan_stats_count = (await session.execute(select(func.count(UserPlanStat.id)))).scalar()
        
    snapshot = {
        "users_count": users_count,
        "habits_count": habits_count,
        "plans_count": plans_count,
        "plan_habits_count": plan_habits_count,
        "user_plans_count": user_plans_count,
        "daily_logs_count": daily_logs_count,
        "daily_summaries_count": daily_summaries_count,
        "user_stats_count": user_stats_count,
        "user_plan_stats_count": user_plan_stats_count
    }
    
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Database snapshot generated at {output_path}: {snapshot}")
    return snapshot

async def seed_production_scale(client):
    """
    Phase 15 Seeding:
      - 8-10 users
      - 50-100 habits (mix of public and private)
      - 20-30 public plans
      - 5-10 private plans
      - Attach 3-10 habits per plan
      - Activate plan for each user
      - Simulate 14 days
      - Verify integrity
      - Save database snapshot
    """
    print("Seeding production scale data through APIs...")
    
    # 1. Register and login 9 Users
    user_roles = [
        "Student", "Software Engineer", "UPSC Aspirant", "Fitness Enthusiast", 
        "Entrepreneur", "Researcher", "Creator", "Working Professional", "Manager"
    ]
    users = []
    
    for role in user_roles:
        email = f"{role.lower().replace(' ', '_')}@lifeos.com"
        # Register
        reg_resp = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "password123",
            "timezone": "UTC"
        })
        assert reg_resp.status_code == 201, f"Registration failed for {email}: {reg_resp.text}"
        
        # Login
        log_resp = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "password123"
        })
        assert log_resp.status_code == 200, f"Login failed for {email}: {log_resp.text}"
        
        token_data = log_resp.json()["data"]
        users.append({
            "email": email,
            "id": token_data["user_id"],
            "token": token_data["access_token"],
            "role": role
        })
    print(f"Successfully registered and logged in {len(users)} users.")
    
    # 2. Generate Habits (50-100 total)
    # We will generate 40 public habits created by User 1
    # We will generate 5 private habits for each of the 9 users (45 private habits)
    # Total = 85 habits
    habit_ids = []
    public_habit_ids = []
    user_habit_ids_map = {u["id"]: [] for u in users}
    
    # Admin / First User creates public habits
    admin_headers = {"Authorization": f"Bearer {users[0]['token']}"}
    difficulties = ["easy", "medium", "hard"]
    
    habit_names = [
        "Drink Water", "Morning Jog", "Meditation", "Read Books", "Code Review", 
        "Write Journal", "Plan Day", "Review Budget", "Solve LeetCode", "UPSC Prep",
        "Gym Workout", "Walk 10k Steps", "No Sugar", "Deep Work Session", "Stretch",
        "Clean Desk", "Water Plants", "Call Family", "Bed by 10 PM", "Wake at 5 AM",
        "Healthy Breakfast", "No Social Media", "Check Email", "Team Sync", "Log Food",
        "Practice Guitar", "Learn Languages", "Check Tasks", "Vitamin D Check", "Posture Check",
        "Declutter Room", "Read News", "Write Code", "Plan Tomorrow", "Limit Coffee",
        "Walk after Lunch", "Review Goals", "Gratitude List", "Study Flashcards", "Quick Pushups"
    ]
    
    for name in habit_names:
        h_resp = await client.post("/api/v1/plans/habits", json={
            "name": f"{name} (Public)",
            "category": random.choice(list(HabitCategory)),
            "difficulty": random.choice(difficulties),
            "base_score": random.choice([5, 10, 15, 20]),
            "is_public": True
        }, headers=admin_headers)
        assert h_resp.status_code == 200, f"Failed to create habit: {h_resp.text}"
        h_id = h_resp.json()["data"]["id"]
        public_habit_ids.append(h_id)
        habit_ids.append(h_id)
        
    # Each user creates private habits
    for u in users:
        u_headers = {"Authorization": f"Bearer {u['token']}"}
        private_names = ["Private Focus", "Private Gym", "Private Reflection", "Private Project", "Private Routine"]
        for name in private_names:
            h_resp = await client.post("/api/v1/plans/habits", json={
                "name": f"{name} ({u['role']})",
                "category": random.choice(list(HabitCategory)),
                "difficulty": random.choice(difficulties),
                "base_score": random.choice([5, 10, 15, 20]),
                "is_public": False
            }, headers=u_headers)
            assert h_resp.status_code == 200, f"Failed to create habit: {h_resp.text}"
            h_id = h_resp.json()["data"]["id"]
            user_habit_ids_map[u["id"]].append(h_id)
            habit_ids.append(h_id)
            
    print(f"Generated {len(public_habit_ids)} public habits and {len(users) * 5} private habits (Total: {len(habit_ids)}).")
    
    # 3. Create Plans
    # 25 Public Plans (created by user 0)
    # 7 Private Plans (created by users 1-7)
    plan_ids = []
    
    plan_themes = [
        "Productivity Hack", "Strength Training", "Mental Clarity", "Creative Spark",
        "UPSC Prep Guide", "Clean Eating", "Night Wind-down", "Focus Block",
        "Startup Grind", "Healthy Heart", "Mindfulness Ritual", "Financial discipline",
        "Software Engineering Mastery", "Research Sprint", "Academic Excellence", "Fitness Kickstart",
        "Healthy Sleep Cycle", "Deep Reading", "Guitar Basics", "Language Learning Daily",
        "Time Management Course", "Career Development", "Stress Reliever", "Energy Booster",
        "Daily Minimalism"
    ]
    
    # Generate public plans
    for i, theme in enumerate(plan_themes):
        # Pick 3-10 random habits from public habits
        sample_size = random.randint(3, 8)
        selected_habits = random.sample(public_habit_ids, sample_size)
        
        habits_payload = []
        for j, h_id in enumerate(selected_habits):
            habits_payload.append({
                "habit_id": h_id,
                "start_time": f"{8 + j:02d}:00:00",
                "end_time": f"{10 + j:02d}:00:00",
                "day_config": random.choice(["everyday", "weekdays", "weekends"])
            })
            
        p_resp = await client.post("/api/v1/plans/", json={
            "name": f"{theme} (Public)",
            "difficulty": random.choice(difficulties),
            "is_public": True,
            "habits": habits_payload
        }, headers=admin_headers)
        assert p_resp.status_code == 200, f"Failed to create public plan: {p_resp.text}"
        plan_ids.append(p_resp.json()["data"]["id"])
        
    # Generate private plans (1 per user for users 1 to 7)
    for u in users[1:8]:
        u_headers = {"Authorization": f"Bearer {u['token']}"}
        # Mix public habits and this user's private habits
        sample_public = random.sample(public_habit_ids, random.randint(2, 4))
        user_privates = user_habit_ids_map[u["id"]]
        selected_habits = sample_public + user_privates
        
        habits_payload = []
        for j, h_id in enumerate(selected_habits):
            habits_payload.append({
                "habit_id": h_id,
                "start_time": f"{7 + j:02d}:00:00",
                "end_time": f"{9 + j:02d}:00:00",
                "day_config": random.choice(["everyday", "weekdays"])
            })
            
        p_resp = await client.post("/api/v1/plans/", json={
            "name": f"Private Plan for {u['role']}",
            "difficulty": random.choice(difficulties),
            "is_public": False,
            "habits": habits_payload
        }, headers=u_headers)
        assert p_resp.status_code == 200, f"Failed to create private plan: {p_resp.text}"
        plan_ids.append(p_resp.json()["data"]["id"])
        
    print(f"Generated 25 public plans and 7 private plans (Total: {len(plan_ids)}).")
    
    # 4. Activate plans for all users
    # Assign plan_ids[idx] to users[idx]
    for idx, u in enumerate(users):
        u_headers = {"Authorization": f"Bearer {u['token']}"}
        plan_to_activate = plan_ids[idx]
        act_resp = await client.post(f"/api/v1/plans/{plan_to_activate}/activate", headers=u_headers)
        assert act_resp.status_code == 200, f"Activation failed for User {u['email']}: {act_resp.text}"
        
    print("Activated plans for all users.")
    
    # 5. Run 14-day Simulation
    await run_simulation(client, users, habit_ids, plan_ids, days=14)
    
    # 6. Generate final snapshot
    await generate_database_snapshot()
    print("Scale seeding process fully complete!")

import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


async def main():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as client:
        await seed_production_scale(client)


if __name__ == "__main__":
    asyncio.run(main())