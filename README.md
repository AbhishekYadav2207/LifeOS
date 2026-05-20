# LifeOS Backend Architecture & Comprehensive System Blueprint

## 1. Executive Overview

LifeOS Backend is a high-performance, asynchronously driven behavioral enforcement and tracking system designed for absolute data integrity, scalable execution, and advanced psychological conditioning via scoring and ranking metrics. It is built as a highly robust RESTful API that interfaces with an isolated Flutter mobile client, providing an uncompromising foundation for the LifeOS platform. 

This document serves as the exhaustive specification for the application, detailing every structural layer, API endpoint, database schema, and scoring heuristic deployed.

---

## 2. Core Technologies & Stack Matrix

The backend relies on modern, cutting-edge Python standards to ensure concurrent execution and strict typing.

* **Primary Framework**: **FastAPI** — Chosen for its Starlette-based asynchronous capabilities and seamless integration with Pydantic for validation. It guarantees blazing-fast concurrent request handling with minimal overhead.
* **Database Engine**: **SQLite (Async)** via `aiosqlite`. While currently configured for localized fast development and deployment, the abstraction layer is explicitly designed for a seamless, zero-downtime migration to PostgreSQL in production environments.
* **ORM & Migrations**: **SQLAlchemy (v2.0+)** paired with **Alembic**. SQLAlchemy acts as the relational object mapper enforcing referential integrity, while Alembic maintains rigid, version-controlled schema definitions across iterations.
* **Data Validation & Serialization**: **Pydantic (v2)** — Implements strict, mathematically provable data contract enforcement at the boundary layer, completely preventing malformed payloads from entering the business logic.
* **Security & Authentication**: **JSON Web Tokens (JWT)** combined with **BCrypt** hashing. Passwords are never stored in plaintext, and session security is managed via stateless tokens with configurable expirations.
* **Server Infrastructure**: **Uvicorn** — Provides a robust ASGI-compliant runtime, efficiently dispatching incoming HTTP traffic to the FastAPI event loop.

---

## 3. Deep-Dive System Architecture

The application strictly adheres to Domain-Driven Design (DDD) principles, leveraging a modular, dependency-injected architecture divided into highly cohesive, loosely coupled segments.

### 3.1. The Data Lifecycle & State Machine
1. **Plans Engine System**: User intents (`UserPlan`) are dynamically mapped to specific behavioral criteria (`Habit` -> `PlanHabit`). Because human behavior is non-linear, modifications to a User's Plan (or new subscriptions) apply on their *next temporal day boundary*. This guarantees that mid-day changes do not corrupt active executions.
2. **Immutable Snapshot Logs**: Executions (`DailyLogs`) are preserved as immutable snapshots. If a root `Habit` changes its severity or base scoring parameters internally, past aggregated statistics stay utterly unchanged. The logs are a cryptographic-style ledger of past behavior.
3. **Execution Service Boundary**: The `/today` boundary dynamically aggregates localized temporal parameters to generate "Pending" logs against active user constraints. It is timezone-aware and respects the localized midnight of the end-user.
4. **Scoring Service Engine**: Evaluates behaviors asynchronously or via a cron-triggered `/process-day`. "Pending" events regress to failure states (imposing a static 50% penalty on total daily gains), driving an incremental, highly concurrent `UserStat` streak update matrix that calculates long-term viability.

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
* `POST /auth/login`: Authenticates user credentials.
  * **Payload**: `email`, `password`.
  * **Response**: Returns a localized session JWT token.

### 5.2. Habit Management Operations
* `GET /habits/public`: Retrieves the global catalog of community habits. Supports `category` query filters.
* `GET /habits/mine`: Retrieves authenticated user's private habits.
* `POST /habits/`: Creates a new foundational habit.
  * **Payload**: `name`, `category`, `difficulty`, `base_score` (optional), `is_public` (optional).
* `PUT /habits/{habit_id}`: Updates existing parameters of a habit dynamically.
* `DELETE /habits/{habit_id}`: Soft-deletes or completely purges a habit.

### 5.3. Plan Management Operations
* `GET /plans/`: Lists available macroscopic plans.
* `POST /plans/`: Constructs a new plan encapsulating multiple habits.
  * **Payload**: `name`, `difficulty`, `habits` (array of IDs), `is_public`.
* `POST /plans/select-plan`: Subscribes the authenticated user to a specific plan.
  * **Payload**: `plan_id`, `start_date`.

### 5.4. Execution & Daily Logging Operations
* `GET /today/`: Dynamically computes and returns the user's localized execution requirements for the current 24-hour cycle.
* `POST /today/habit/complete`: The most critical endpoint. Transmits proof of execution to the backend.
  * **Payload**: `habit_id`, `note` (optional context).
* `POST /today/process`: Forces the chron-boundary processing logic to evaluate unhandled pending logs into failed states and compute statistical rank degradation.

### 5.5. Statistical & Profile Operations
* `GET /stats/profile`: Returns the user's aggregated `UserStat` record, containing current total points, historical streak metrics, and current computed ranking tier.

---

## 6. Setup, Configuration & Deployment

Follow these strict procedures to initialize the backend environment securely in a localized or production setting.

### 6.1. Environment Configuration
Create a `.env` file in the root directory and configure the fundamental environmental overrides:
```env
DATABASE_URL="sqlite+aiosqlite:///./lifeos.db"
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
Provision the SQLite database by running Alembic forward to the `head` revision, which constructs the tables dynamically based on SQLAlchemy models:
```bash
alembic upgrade head
```

### 6.5. ASGI Server Invocation
Run the server using Uvicorn. The `--reload` flag provides hot-reloading for local development:
```bash
uvicorn app.main:app --reload
```

### 6.6. Comprehensive Test Suite
Validate the entire scoring matrix, boundary limits, and authentication logic via PyTest:
```bash
pytest
```

---

## 7. Dynamic API Documentation

When the server is running locally on port 8000, FastAPI automatically exposes OpenAPI-compliant documentation environments. These are automatically updated dynamically upon any schema changes in the codebase.
* **Swagger UI (Interactive)**: `http://127.0.0.1:8000/docs`
* **ReDoc (Static Layout)**: `http://127.0.0.1:8000/redoc`
