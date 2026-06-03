# Project Analysis Report

## 1. Application Architecture
The project is a FastAPI-based backend architecture implementing a gamified habit-tracking ecosystem called **LifeOS**.
* **Router Structure**: Located in `app/api/`. It covers authentication (`auth.py`), habits (`habits.py`), plans (`plans.py`), today's execution (`today.py`), and stats/day-closing processing (`stats.py`).
* **Service Structure**: Business logic is separated into service modules in `app/services/`: `user_svc.py`, `plan_svc.py`, `execution_svc.py`, and `scoring_svc.py`.
* **Dependency Injection**: Located in `app/api/dependencies.py`. It injects the database session (`get_db`) and parses the JWT token to fetch the current user (`get_current_user`).
* **Auth Flow**: Uses JSON Web Tokens (JWT) signed with HS256. Clients register and log in to receive a token. Authenticated requests include the token in the `Authorization: Bearer <token>` header.
* **Database Flow**: Uses SQLAlchemy ORM with async SQLite database `sqlite+aiosqlite`. Session is yielded per request using an async generator dependency.

## 2. Database Table Details

### Table: `users`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| email | VARCHAR | False | False | None |
| password_hash | VARCHAR | False | False | None |
| timezone | VARCHAR | False | False | UTC |
| created_at | DATETIME | True | False | None |
| updated_at | DATETIME | True | False | None |

**Indexes**:
* `ix_users_id`: unique=False, columns=['id'], where=None
* `ix_users_email`: unique=True, columns=['email'], where=None

---

### Table: `habits`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| name | VARCHAR | False | False | None |
| category | VARCHAR(10) | False | False | None |
| difficulty | VARCHAR | False | False | None |
| base_score | INTEGER | False | False | 10 |
| created_by | INTEGER | False | False | None |
| is_public | BOOLEAN | True | False | True |

**Foreign Keys**:
* `created_by` -> `users.id` (ondelete: None)

**Unique Constraints**:
* `uix_habit_name_creator`: columns `['name', 'created_by']`

**Indexes**:
* `ix_habits_id`: unique=False, columns=['id'], where=None
* `ix_habits_name`: unique=False, columns=['name'], where=None

---

### Table: `plans`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| name | VARCHAR | False | False | None |
| created_by | INTEGER | False | False | None |
| is_public | BOOLEAN | True | False | False |
| difficulty | VARCHAR | False | False | None |

**Foreign Keys**:
* `created_by` -> `users.id` (ondelete: None)

**Indexes**:
* `ix_plans_name`: unique=False, columns=['name'], where=None
* `ix_plans_id`: unique=False, columns=['id'], where=None

---

### Table: `plan_habits`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| plan_id | INTEGER | False | False | None |
| habit_id | INTEGER | False | False | None |
| start_time | TIME | True | False | None |
| end_time | TIME | True | False | None |
| day_config | VARCHAR | True | False | everyday |

**Foreign Keys**:
* `habit_id` -> `habits.id` (ondelete: CASCADE)
* `plan_id` -> `plans.id` (ondelete: CASCADE)

**Indexes**:
* `ix_plan_habits_id`: unique=False, columns=['id'], where=None

---

### Table: `user_plans`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| user_id | INTEGER | False | False | None |
| plan_id | INTEGER | False | False | None |
| active | BOOLEAN | True | False | True |
| start_date | DATE | False | False | None |
| end_date | DATE | True | False | None |

**Foreign Keys**:
* `plan_id` -> `plans.id` (ondelete: CASCADE)
* `user_id` -> `users.id` (ondelete: CASCADE)

**Indexes**:
* `ix_user_plans_id`: unique=False, columns=['id'], where=None
* `uix_one_active_plan`: unique=True, columns=['user_id'], where=None

---

### Table: `daily_logs`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| user_id | INTEGER | False | False | None |
| plan_id | INTEGER | True | False | None |
| habit_id | INTEGER | True | False | None |
| snapshot_habit_name | VARCHAR | False | False | None |
| category | VARCHAR(10) | False | False | None |
| snapshot_difficulty | VARCHAR | False | False | None |
| snapshot_base_score | INTEGER | False | False | None |
| date | DATE | False | False | None |
| status | VARCHAR | False | False | pending |
| completion_timestamp | DATETIME | True | False | None |
| note | VARCHAR | True | False | None |
| late_flag | BOOLEAN | True | False | False |
| awarded_points | INTEGER | False | False | 0 |

**Foreign Keys**:
* `plan_id` -> `plans.id` (ondelete: SET NULL)
* `user_id` -> `users.id` (ondelete: CASCADE)
* `habit_id` -> `habits.id` (ondelete: SET NULL)

**Unique Constraints**:
* `uix_user_habit_date`: columns `['user_id', 'habit_id', 'date']`

**Indexes**:
* `ix_daily_logs_date`: unique=False, columns=['date'], where=None
* `ix_daily_logs_user_id`: unique=False, columns=['user_id'], where=None
* `ix_daily_logs_id`: unique=False, columns=['id'], where=None

---

### Table: `daily_summaries`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| user_id | INTEGER | False | False | None |
| date | DATE | False | False | None |
| total_score_change | INTEGER | False | False | 0 |

**Foreign Keys**:
* `user_id` -> `users.id` (ondelete: CASCADE)

**Unique Constraints**:
* `uix_user_date`: columns `['user_id', 'date']`

**Indexes**:
* `ix_daily_summaries_user_id`: unique=False, columns=['user_id'], where=None
* `ix_daily_summaries_id`: unique=False, columns=['id'], where=None

---

### Table: `user_stats`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| user_id | INTEGER | False | False | None |
| total_points | INTEGER | False | False | 0 |
| current_streak | INTEGER | False | False | 0 |
| max_streak | INTEGER | False | False | 0 |
| focus_points | INTEGER | False | False | 0 |
| health_points | INTEGER | False | False | 0 |
| discipline_points | INTEGER | False | False | 0 |
| mind_points | INTEGER | False | False | 0 |

**Foreign Keys**:
* `user_id` -> `users.id` (ondelete: CASCADE)

**Unique Constraints**:
* `None`: columns `['user_id']`

**Indexes**:
* `ix_user_stats_id`: unique=False, columns=['id'], where=None

---

### Table: `user_plan_stats`
| Column | Type | Nullable | Primary Key | Default |
|---|---|---|---|---|
| id | INTEGER | False | True | None |
| user_id | INTEGER | False | False | None |
| plan_id | INTEGER | False | False | None |
| total_points | INTEGER | False | False | 0 |
| current_streak | INTEGER | False | False | 0 |
| max_streak | INTEGER | False | False | 0 |
| focus_points | INTEGER | False | False | 0 |
| health_points | INTEGER | False | False | 0 |
| discipline_points | INTEGER | False | False | 0 |
| mind_points | INTEGER | False | False | 0 |

**Foreign Keys**:
* `user_id` -> `users.id` (ondelete: CASCADE)
* `plan_id` -> `plans.id` (ondelete: CASCADE)

**Indexes**:
* `ix_user_plan_stats_id`: unique=False, columns=['id'], where=None
* `ix_user_plan_stats_user_id`: unique=False, columns=['user_id'], where=None

---

