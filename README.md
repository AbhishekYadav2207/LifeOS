# LifeOS Backend Architecture & Comprehensive System Blueprint

## 1. Executive Overview

LifeOS Backend is a high-performance, asynchronously driven behavioral enforcement and tracking system designed for absolute data integrity, scalable execution, and advanced psychological conditioning via scoring and ranking metrics. It is built as a highly robust RESTful API that interfaces with an isolated Flutter mobile client, providing an uncompromising foundation for the LifeOS platform. 

This document serves as the exhaustive specification for the application, detailing every structural layer, API endpoint, database schema, and scoring heuristic deployed.

---

## 2. Core Technologies & Stack Matrix

The backend relies on modern, cutting-edge Python standards to ensure concurrent execution and strict typing.

* **Primary Framework**: **FastAPI** — Chosen for its Starlette-based asynchronous capabilities and seamless integration with Pydantic for validation. It guarantees blazing-fast concurrent request handling with minimal overhead.
* **Database Engine**: **PostgreSQL (Async)** via `asyncpg`. Configured for robust production-ready concurrent execution with native transaction isolation.
* **ORM & Migrations**: **SQLAlchemy (v2.0+)** paired with **Alembic**. SQLAlchemy acts as the relational object mapper enforcing referential integrity, while Alembic maintains rigid, version-controlled schema definitions across iterations.
* **Data Validation & Serialization**: **Pydantic (v2)** — Implements strict, mathematically provable data contract enforcement at the boundary layer, completely preventing malformed payloads from entering the business logic.
* **Security & Authentication**: **JSON Web Tokens (JWT)** combined with **BCrypt** hashing. Passwords are never stored in plaintext, and session security is managed via stateless tokens with configurable expirations.
* **Server Infrastructure**: **Uvicorn** — Provides a robust ASGI-compliant runtime, efficiently dispatching incoming HTTP traffic to the FastAPI event loop.

---

## 3. Deep-Dive System Architecture

The application strictly adheres to Domain-Driven Design (DDD) principles, leveraging a modular, dependency-injected architecture divided into highly cohesive, loosely coupled segments.

### 3.1. The Data Lifecycle & State Machine
1. **Plans Engine System**: User intents (`UserPlan`) are dynamically mapped to specific behavioral criteria (`Habit` -> `PlanHabit`). Plan activation (`POST /api/v1/plans/{plan_id}/activate`) takes effect **today**, deactivating previous active user plans by setting their `end_date = local_today` and starting the new plan on the same day (`start_date = local_today`).
2. **Immutable Snapshot Logs**: Executions (`DailyLogs`) are preserved as immutable snapshots. If a root `Habit` changes its severity or base scoring parameters internally, past completed log statistics stay unchanged.
3. **Execution Service Boundary**: The `/api/v1/today/` boundary dynamically aggregates localized temporal parameters based on the user's timezone to generate "Pending" logs against the active plan. It automatically executes a backfill processing for any unprocessed days prior to today (up to a 7-day limit).
4. **Scoring Service Engine**: Evaluates behaviors via `/api/v1/today/process` (manually or as part of day transition) or during auto-backfills. "Pending" events regress to failure states (imposing a 50% penalty deduction of `-(base_score // 2)`), updating total points (with a floor of 0) and streaks (reset to 0 if any task is missed; incremented if all are completed).

### 3.2. Directory & Module Structure
* `app/api/`: Routing layer containing all FastAPI routers broken down by domain (Auth, Habits, Plans, Stats, Execution).
* `app/core/`: Security implementations, hashing functions, JWT encoding/decoding, configuration singletons, and core dependency overrides.
* `app/models/`: SQLAlchemy declarative base classes representing the exact physical database schema.
* `app/schemas/`: Pydantic models handling Request/Response validation.
* `app/services/`: The core business logic. FastAPI routes are incredibly thin, delegating all operations to these service classes to ensure unit-testability without HTTP mocking.
* `alembic/`: Migration scripts mapping the delta between code state and physical database state.

---

## 4. Comprehensive Feature & Capability Breakdown

### 4.1. Intelligent Habit Catalog
Habits form the foundational atomic unit of LifeOS. They are defined completely independently of users and support:
* **Custom Categorization**: High-level semantic grouping (e.g., Fitness, Mental, Work).
* **Tiered Difficulty Metrics**: Habits are classified by exertion load, which directly impacts their multiplier logic.
* **Base Scoring Logic Rules**: Each habit contains an inherent value that dictates how much progress a user makes towards their next rank.
* **Public/Private States**: Habits can be published globally to a community catalog or kept completely private to a specific user.

### 4.2. Aggregated Plan Configurations
Plans are structured collections of habits. Instead of subscribing to individual habits manually, users subscribe to Plans.
* **Time Windows**: Collections of behaviors can be constrained by custom time windows.
* **Historical Integrity**: A `PlanHabit` bridging table connects habits to plans, allowing a plan to evolve while retaining execution integrity for active subscribers.

### 4.3. The Core Scoring Matrix (Algorithmic Details)
The scoring engine is the heart of the behavioral conditioning loop:
* **Completed (100%)**: Natively awards the `Base Score` defined in the habit.
* **Late (50% Penalty)**: Heuristically detected via the `late_flag`. If a user completes a habit outside of the designated optimal window, the system penalizes the completion by awarding only 50% of the base score.
* **Missed (Negative Degradation)**: Automated negative degradation. When the `/process-day` boundary crosses midnight and pending tasks remain unresolved, the system dynamically deducts points to actively punish non-compliance.

### 4.4. Global Ranking Ecosystem
A comprehensive 9-tier hierarchical rank system designed for long-term psychological incentivization based on a sustained adherence scale. The thresholds are mathematically modeled for logarithmic difficulty progression:
1. **Beginner** (0 - 50 points)
2. **Starter** (50 - 150 points)
3. **Rising** (150 - 300 points)
4. **Consistent** (300 - 500 points)
5. **Focused** (500 - 800 points)
6. **Disciplined** (800 - 1200 points)
7. **Advanced** (1200 - 1800 points)
8. **Elite** (1800 - 2500 points)
9. **Master** (2500+ points)

---

## 5. Exhaustive API Specification

All endpoints are prefixed with `/api/v1` and utilize strict JSON request/response formats mapped precisely to Pydantic schemas. Standardized responses wrap all data in a `BaseResponse` object containing `success`, `data`, `message`, and `meta` fields.

### 5.1. Authentication Operations
* `POST /api/v1/auth/register`: Signs up a user given a JSON of `email`, `password`, and optional `timezone`.
* `POST /api/v1/auth/login`: Authenticates user credentials and issues a JWT token.
  * **Payload**: `email`, `password`.
  * **Response**: Returns a Bearer access token.

### 5.2. Habit Management Operations
* `GET /api/v1/habits/public`: Retrieves the global catalog of community habits. Supports `category` query filters.
* `GET /api/v1/habits/mine`: Retrieves authenticated user's private habits.
* `POST /api/v1/habits/`: Creates a new foundational habit.
  * **Payload**: `name`, `category`, `difficulty`, `base_score` (optional), `is_public` (optional).
* `PUT /api/v1/habits/{habit_id}`: Updates existing parameters of a habit dynamically (owner only).
* `DELETE /api/v1/habits/{habit_id}`: Purges a habit (owner only).

### 5.3. Plan Management Operations
* `GET /api/v1/plans/`: Lists available public plans.
* `GET /api/v1/plans/mine`: Lists plans created by the authenticated user.
* `POST /api/v1/plans/`: Constructs a new plan encapsulating multiple habits.
  * **Payload**: `name`, `difficulty`, `habits` (array of `PlanHabitCreate` mapping `habit_id`, `start_time`, `end_time`, `day_config`), `is_public`.
* `PUT /api/v1/plans/{plan_id}`: Updates a plan's fields and habit mappings (owner only).
* `DELETE /api/v1/plans/{plan_id}`: Deletes a plan (owner only).
* `POST /api/v1/plans/{plan_id}/activate`: Deactivates old user plans and activates the given plan starting today.
* `GET /api/v1/plans/{plan_id}/habits`: Lists habits associated with a specific plan (returns timing metadata).

### 5.4. Execution & Daily Logging Operations
* `GET /api/v1/today/`: Dynamically computes, triggers backfill processing for up to 7 unprocessed past days, and returns the user's localized execution logs for the current day.
* `POST /api/v1/today/habit/complete`: Updates a pending daily log to "done", assigning its `late_flag` based on timing constraints.
  * **Payload**: `habit_id`, `note` (optional context).
* `POST /api/v1/today/process`: Forces day processing: marks pending logs as missed, applies penalties, updates streaks/ranks.

### 5.5. Statistical & Profile Operations
* `GET /api/v1/stats/profile`: Returns the user's aggregated `UserStat` record, containing total points, current streak, max streak, and computed ranking.

---

## 6. Setup, Configuration & Deployment

Follow these strict procedures to initialize the backend environment securely in a localized or production setting.

### 6.1. Environment Configuration
Create a `.env` file in the root directory and configure the fundamental environmental overrides:
```env
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos789@localhost:5432/lifeos"
SECRET_KEY="<strong-cryptographic-hash>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 6.2. Virtual Environment Allocation
Isolate the dependency tree to prevent global system state corruption:
```bash
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows platforms
```

### 6.3. Dependency Resolution
Pull down all locked dependencies using pip:
```bash
pip install -r requirements.txt
```

### 6.4. Database Migration Pipeline
Provision the PostgreSQL database by running Alembic forward to the `head` revision, which constructs the tables dynamically based on SQLAlchemy models:
```bash
alembic upgrade head
```

### 6.5. ASGI Server Invocation
Run the server using Uvicorn. The `--reload` flag provides hot-reloading for local development:
```bash
uvicorn app.main:app --reload
```

### 6.6. Comprehensive Test Suite & Seeding
Validate the entire scoring matrix, boundary limits, and authentication logic via PyTest or run the autonomous test runner and database seeder:
* **Standard PyTest**:
  ```bash
  pytest
  ```
* **Autonomous Seeder & QA Tester**:
  ```bash
  venv\Scripts\python tests/auto_tester.py
  ```
  This command will clean the test database, seed 8-10 users, 50-100 habits, 20-30 plans, simulate 14 days of realistic usage, compile reports, and write `database_snapshot.json`.

---

## 7. Dynamic API Documentation

When the server is running locally on port 8000, FastAPI automatically exposes OpenAPI-compliant documentation environments. These are automatically updated dynamically upon any schema changes in the codebase.
* **Swagger UI (Interactive)**: `http://127.0.0.1:8000/docs`
* **ReDoc (Static Layout)**: `http://127.0.0.1:8000/redoc`
