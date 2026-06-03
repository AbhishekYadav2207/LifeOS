# LifeOS V1 - API Documentation

## 1. System Overview
LifeOS V1 Backend Architecture. The API enables clients to interact with habit tracking, scoring, daily logs, and stats tracking. High-level flow involves Plan creation, execution logging, stats tracking and scoring.

## 2. API Summary Table

| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | /api/v1/auth/register | Register a new user and initialize stats | No |
| POST | /api/v1/auth/login | Login and issue JWT access token | No |
| GET | /api/v1/plans/ | List all public plans | No |
| GET | /api/v1/plans/mine | List my plans | Yes |
| POST | /api/v1/plans/ | Create a new plan | Yes |
| PUT | /api/v1/plans/{plan_id} | Update a plan (owner only) | Yes |
| DELETE | /api/v1/plans/{plan_id} | Delete a plan (owner only) | Yes |
| POST | /api/v1/plans/{plan_id}/activate | Activate a plan starting today | Yes |
| GET | /api/v1/plans/{plan_id}/habits | Get habits configuration for a plan | Yes |
| GET | /api/v1/habits/public | List public habits | No |
| GET | /api/v1/habits/mine | List my habits | Yes |
| POST | /api/v1/habits/ | Create a new habit | Yes |
| PUT | /api/v1/habits/{habit_id} | Update a habit (owner only) | Yes |
| DELETE | /api/v1/habits/{habit_id} | Delete a habit (owner only) | Yes |
| GET | /api/v1/today/ | Get/Initialize today's logs (triggers backfill) | Yes |
| POST | /api/v1/today/habit/complete | Complete a pending habit log | Yes |
| POST | /api/v1/today/process | Close day & update streaks/ranks | Yes |
| GET | /api/v1/stats/profile | Get profile metrics, streak, and rank | Yes |
| GET | / | Root / Service Health Check | No |

## 3. Endpoint Documentation (DETAILED)

### POST /api/v1/auth/register
**Purpose**: Register

#### Request
- **Auth Required**: No
- **Body Schema**:
  - Model: `UserCreate`
    - `email` (string): Email (Required)
    - `password` (string): Password (Required)
    - `timezone` (string): Timezone (Optional, defaults to `"UTC"`)

#### Response
- **201**: Successful Response
  - Returns `BaseResponse_UserResponse_`
    - `success`: boolean
    - `data`: `UserResponse` (`id`, `email`, `timezone`)
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
* Hashes the password using BCrypt.
* Validates that the email is unique in the system.
* Integrates timezone checking. Default is `"UTC"`.

#### Database Impact
* Inserts a record into the `users` table.
* Automatically creates an associated `user_stats` record with default values: points = 0, current_streak = 0, max_streak = 0, last_processed_date = null.

#### Validation Rules
* Pydantic validation ensures fields are populated.
* Email must be a valid email format.

#### Edge Cases
* Submitting an email that is already registered returns a `400 Bad Request` with "Email already registered".
* Submitting an invalid timezone format defaults to `"UTC"` or raises validation constraints depending on the validation schema.

#### Security
- **Auth Required**: No

---

### POST /api/v1/auth/login
**Purpose**: Login

#### Request
- **Auth Required**: No
- **Body Schema**:
  - Model: `UserLogin`
    - `email` (string): Email (Required)
    - `password` (string): Password (Required)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_TokenData_`
    - `success`: boolean
    - `data`: `TokenData` (`access_token`, `token_type` = `"bearer"`)
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
* Verifies password hash using BCrypt.
* Generates a JWT access token containing the user's ID as the subject (`sub`). Expiration is configured to 30 minutes.

#### Database Impact
* Queries the `users` table to locate the user by email. No writes are performed.

#### Validation Rules
* Email and password are required.

#### Edge Cases
* Incorrect email or wrong password returns a `401 Unauthorized` response with "Incorrect email or password".

#### Security
- **Auth Required**: No

---

### GET /api/v1/plans/public
**Purpose**: List public plans

#### Request
- **Auth Required**: No
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_PlanResponse__`
    - `success`: boolean
    - `data`: List of `PlanResponse` (`id`, `name`, `created_by`, `is_public`, `difficulty`, `habits_count`)
    - `message`: string
    - `meta`: any

#### Business Logic
* Queries the `plans` table for records where `is_public == True`.
* Calculates the number of habits linked to each plan using a correlated subquery.

#### Database Impact
* Performs a SELECT query on `plans` and `plan_habits`. No writes.

#### Validation Rules
* None.

#### Edge Cases
* Returns an empty list `[]` if no public plans are available.

#### Security
- **Auth Required**: No

---

### GET /api/v1/plans/mine
**Purpose**: List my plans

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_PlanResponse__`
    - `success`: boolean
    - `data`: List of `PlanResponse`
    - `message`: string
    - `meta`: any

#### Business Logic
* Filters the `plans` table to only return plans where `created_by` matches the current logged-in user.
* Includes `habits_count` per plan.

#### Database Impact
* SELECT query on `plans` and `plan_habits`. No writes.

#### Validation Rules
* Bearer token must be provided and valid.

#### Edge Cases
* Returns `[]` if the user has not created any plans.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### POST /api/v1/plans/
**Purpose**: Create a new plan

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `PlanCreate`
    - `name` (string): Name (Required)
    - `is_public` (boolean): Is Public (Optional, defaults to `False`)
    - `difficulty` (string): Difficulty (`easy`, `medium`, `hard`) (Required)
    - `habits` (array of `PlanHabitCreate`): Habits mapping with `habit_id`, `start_time` (optional), `end_time` (optional), `day_config` (optional, default `"everyday"`)

#### Response
- **201**: Successful Response
  - Returns `BaseResponse_PlanResponse_`
    - `success`: boolean
    - `data`: `PlanResponse`
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`

#### Business Logic
* Checks if all provided `habit_id` values exist and are accessible (either public, or created by the current user).
* Prevents placing private habits inside a public plan.
* Creates the plan and links habits to it.

#### Database Impact
* Inserts a record into the `plans` table.
* Inserts multiple records into the `plan_habits` table.

#### Validation Rules
* Habits list is validated. If `is_public` is true, all referenced habits must have `is_public == True` or else returns `400 Bad Request`.

#### Edge Cases
* If any referenced `habit_id` is invalid or not owned by the user, returns a `404 Not Found` response with "One or more habit IDs do not exist or are not accessible".
* Attempting to link a private habit in a public plan returns `400 Bad Request` with "Cannot include private habits in a public plan".

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### PUT /api/v1/plans/{plan_id}
**Purpose**: Update a plan

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `PlanCreate` (fields identical to POST `/api/v1/plans/`)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_PlanResponse_`
- **422**: Validation Error

#### Business Logic
* Verifies that the plan exists and is owned by the current user.
* Verifies that all habit IDs are valid and accessible.
* Performs replacement update: deletes existing plan habits and inserts the new list.

#### Database Impact
* Updates the `plans` record.
* DELETES existing associations in `plan_habits` for this plan.
* INSERTS new associations in `plan_habits`.

#### Validation Rules
* User must be the owner. Same rules as creation apply.

#### Edge Cases
* If the plan does not exist, returns `404 Not Found` with "Plan not found".
* If the user is not the creator, returns `403 Forbidden` with "Not your plan".

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### DELETE /api/v1/plans/{plan_id}
**Purpose**: Delete a plan

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse`

#### Business Logic
* Verifies plan ownership. Deletes the plan from the database.
* Associated plan habits and user plan subscription maps are cascade-deleted.

#### Database Impact
* DELETES the plan row from `plans`. Cascade triggers delete matching entries in `plan_habits` and `user_plans`.

#### Validation Rules
* User must be the owner.

#### Edge Cases
* If the plan does not exist, returns `404 Not Found`.
* If user is not the owner, returns `403 Forbidden`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### POST /api/v1/plans/{plan_id}/activate
**Purpose**: Activate a plan for the current user

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse`

#### Business Logic
* Verifies the plan is public or owned by the user.
* Determines the user's current date based on their timezone.
* Deactivates all currently active plans by setting `active = False` and `end_date = local_today`.
* Activates the new plan starting today (`start_date = local_today`, `active = True`).

#### Database Impact
* Updates old active user plans in the `user_plans` table.
* Inserts a new row in the `user_plans` table.

#### Validation Rules
* Plan must be accessible.

#### Edge Cases
* Activating an inaccessible private plan owned by another user returns `403 Forbidden` with "Cannot activate a private plan you did not create".
* Plan not found returns `404 Not Found`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### GET /api/v1/plans/{plan_id}/habits
**Purpose**: Get habits for a specific plan

#### Request
- **Auth Required**: Yes (to verify access to private plans)
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__` (mapped as `PlanHabitTimelineResponse` including `start_time`, `end_time`, and `day_config`)

#### Business Logic
* Checks plan visibility (must be public or owned by the user).
* Returns all habits linked to the plan, pre-loaded using SQLAlchemy `selectinload` to avoid N+1 queries.

#### Database Impact
* SELECT query on `plans`, `plan_habits`, and `habits`. No writes.

#### Validation Rules
* Auth token must be provided to inspect private plans.

#### Edge Cases
* Requesting habits for a plan that is private and owned by another user returns `403 Forbidden` with "Cannot view habits of a private plan you do not own".
* Plan not found returns `404 Not Found`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### GET /api/v1/habits/public
**Purpose**: List public habits

#### Request
- **Auth Required**: No
- **Query Parameters**:
  - `category` (string) (Optional) - Filter habits by category tag.

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__`

#### Business Logic
* Retrieves all habits from the catalog where `is_public == True`.
* Filters by category if the query parameter is provided.

#### Database Impact
* SELECT query on `habits` table. No writes.

#### Validation Rules
* None.

#### Edge Cases
* Returns `[]` if no habits match the query.

#### Security
- **Auth Required**: No

---

### GET /api/v1/habits/mine
**Purpose**: List my habits

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__`

#### Business Logic
* Filters habits created by the current user (`created_by == current_user.id`).

#### Database Impact
* SELECT query on `habits`. No writes.

#### Validation Rules
* Valid auth token.

#### Edge Cases
* Returns `[]` if the user has no private/custom habits.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### POST /api/v1/habits/
**Purpose**: Create a new habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `HabitCreate`
    - `name` (string): Name (Required)
    - `category` (string): Category (Required)
    - `difficulty` (string): Difficulty (`easy`, `medium`, `hard`) (Required)
    - `base_score` (integer): Base Score (Optional, defaults to `10`)
    - `is_public` (boolean): Is Public (Optional, defaults to `True`)

#### Response
- **201**: Successful Response
  - Returns `BaseResponse_HabitResponse_`
- **422**: Validation Error

#### Business Logic
* Creates and registers a new habit.
* Enforces that the combination of `(name, created_by)` is unique in the system.

#### Database Impact
* Inserts a record into the `habits` table.

#### Validation Rules
* Unique constraint: A user cannot create two habits with the same name.

#### Edge Cases
* Creating a habit with a name that the user already used raises a `400 Bad Request` or database constraint error.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### PUT /api/v1/habits/{habit_id}
**Purpose**: Update a habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `HabitCreate`

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_HabitResponse_`

#### Business Logic
* Verifies habit exists and is owned by the user.
* Updates values (name, category, difficulty, base_score, is_public).

#### Database Impact
* Updates matching row in the `habits` table.

#### Validation Rules
* User must be the creator. Name uniqueness rules apply.

#### Edge Cases
* Habit not found returns `404 Not Found`.
* Attempting to modify a habit created by another user returns `403 Forbidden`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### DELETE /api/v1/habits/{habit_id}
**Purpose**: Delete a habit

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse`

#### Business Logic
* Verifies habit ownership. Deletes the habit.
* Any plan-habits mapping and completed log histories are cascade deleted.

#### Database Impact
* DELETES row from `habits`. Cascade deletes matching items in `plan_habits` and `daily_logs`.

#### Validation Rules
* User must be the owner.

#### Edge Cases
* Habit not found returns `404 Not Found`.
* Deleting another user's habit returns `403 Forbidden`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### GET /api/v1/today/
**Purpose**: Get Today

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_TodayResponse_` (`logs` list, `date`, `processed`)

#### Business Logic
* Determines the user's current date based on their timezone.
* **Auto-Backfill**: Identifies unprocessed dates between the last processed date and yesterday. Runs daily processing sequentially for these days (maximum 7 days backfill limit).
* Checks if logs for today are already initialized. If not, fetches the user's active plan, filters habits based on their `day_config` weekday/weekend constraint, and inserts new `"pending"` daily log entries.
* Returns today's log entries.

#### Database Impact
* SELECT queries on `user_plans`, `plan_habits`, and `daily_logs`.
* INSERTS `"pending"` logs into `daily_logs`.
* During backfill, updates `daily_logs` to `"missed"` and updates `user_stats`/`user_plan_stats` rows.

#### Validation Rules
* Active plan is required to generate logs. If no active plan exists, returns an empty list.

#### Edge Cases
* If there is no active plan, no logs are generated, returning an empty list of logs.
* If logs were already generated, returns the existing entries (does not duplicate).

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### POST /api/v1/today/habit/complete
**Purpose**: Complete Habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `LogCompletionRequest`
    - `habit_id` (integer): Habit Id (Required)
    - `note` (string): Optional custom note

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_LogResponse_`
- **422**: Validation Error

#### Business Logic
* Finds today's daily log for the user and habit.
* Ensures the log status is `"pending"`.
* Checks the current local time against the habit's `end_time` configuration:
  * If the current time is past `end_time`, `late_flag` is set to `True` and awarded points are halved (`base_score // 2`).
  * If on time, `late_flag` is set to `False` and full `base_score` points are awarded.
* Sets status to `"done"`.

#### Database Impact
* Updates the daily log row in the `daily_logs` table.

#### Validation Rules
* Habit log status must be `"pending"`.

#### Edge Cases
* Completing a habit not scheduled for today or not in pending status returns `400 Bad Request` with "Log not found or not in pending state".
* Submitting for a habit that does not belong to the user returns `404 Not Found` or `403 Forbidden`.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### POST /api/v1/today/process
**Purpose**: Process Day

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_Dict_str__Any__` (`summary` dict)

#### Business Logic
* Processes today's execution details.
* Marks all remaining `"pending"` logs as `"missed"`.
* Applies a missed penalty: `- (base_score // 2)` to points.
* Sums today's total point change and adds it to `user_stats` and `user_plan_stats`.
* Enforces point floor: points cannot drop below 0 (`max(0, points + change)`).
* Streaks:
  * If **any** task is `"missed"`, sets the current streak to `0`.
  * If **all** tasks are `"done"` (and at least 1 task was scheduled), increments the current streak by `1`.
  * If 0 tasks were scheduled, keeps the current streak unchanged.
* Updates the max streak if the current streak exceeds it.
* Updates the user's `last_processed_date` to today's date.

#### Database Impact
* Updates daily logs from `"pending"` to `"missed"`.
* Updates point totals, streaks, and `last_processed_date` in `user_stats` and `user_plan_stats`.
* Inserts a record into the `daily_summaries` table.

#### Validation Rules
* None.

#### Edge Cases
* Can be run multiple times; subsequent calls on the same day are handled gracefully as a no-op or re-evaluate updated completed tasks.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### GET /api/v1/stats/profile
**Purpose**: Get Profile

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_UserStatResponse_` (`points`, `current_streak`, `max_streak`, `rank`)

#### Business Logic
* Retrieves the user's `user_stats` record.
* Dynamically calculates the user's current rank string based on their total points:
  * `< 50`: `"Beginner"`
  * `< 150`: `"Starter"`
  * `< 300`: `"Rising"`
  * `< 500`: `"Consistent"`
  * `< 800`: `"Focused"`
  * `< 1200`: `"Disciplined"`
  * `< 1800`: `"Advanced"`
  * `< 2500`: `"Elite"`
  * `>= 2500`: `"Master"`

#### Database Impact
* SELECT query on `user_stats`. No writes.

#### Validation Rules
* None.

#### Edge Cases
* Returns beginner stats if the user record has not been initialized.

#### Security
- **Auth Required**: Yes (JWT Bearer Token)

---

### GET /
**Purpose**: Root

#### Request
- **Auth Required**: No
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns system details (name, version).

#### Business Logic
* Returns a simple greeting and system health status.

#### Database Impact
* None.

#### Validation Rules
* None.

#### Edge Cases
* None.

#### Security
- **Auth Required**: No
