# LifeOS V1 — API Documentation

## 1. System Overview
LifeOS V1 Backend Architecture. The API enables clients to interact with habit tracking, scoring, daily logs, and stats tracking. High-level flow involves Plan creation, execution logging, stats tracking and scoring.

## 2. API Summary Table

| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | /api/v1/auth/register | Register | No |
| POST | /api/v1/auth/login | Login | No |
| GET | /api/v1/plans/habits | List Habits | No |
| POST | /api/v1/plans/habits | Create Habit | Yes |
| GET | /api/v1/plans/ | List Public Plans | No |
| POST | /api/v1/plans/ | Create Plan | Yes |
| POST | /api/v1/plans/select-plan | Select Plan | Yes |
| GET | /api/v1/execution/today | Get Today | Yes |
| POST | /api/v1/execution/habit/complete | Complete Habit | Yes |
| GET | /api/v1/stats/profile | Get Profile | Yes |
| POST | /api/v1/stats/process-day | Process Day | Yes |
| GET | / | Root | No |

## 3. Endpoint Documentation (DETAILED)

### POST /api/v1/auth/register
**Purpose**: Register

#### Request
- **Auth Required**: No
- **Body Schema**:
  - Model: `UserCreate`
    - `email` (string): Email (Required)
    - `password` (string): Password (Required)
    - `timezone` (string): Timezone (Optional)

#### Response
- **201**: Successful Response
  - Returns `BaseResponse_UserResponse_`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: No)*

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
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: No)*

---

### GET /api/v1/plans/habits
**Purpose**: List Habits

#### Request
- **Auth Required**: No
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: No)*

---

### POST /api/v1/plans/habits
**Purpose**: Create Habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `HabitCreate`
    - `name` (string): Name (Required)
    - `category` (any):  (Required)
    - `difficulty` (string): Difficulty (Required)
    - `base_score` (integer): Base Score (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_HabitResponse_`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### GET /api/v1/plans/
**Purpose**: List Public Plans

#### Request
- **Auth Required**: No
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_PlanResponse__`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: No)*

---

### POST /api/v1/plans/
**Purpose**: Create Plan

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `PlanCreate`
    - `name` (string): Name (Required)
    - `is_public` (boolean): Is Public (Optional)
    - `difficulty` (string): Difficulty (Required)
    - `habits` (array): Habits (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_PlanResponse_`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### POST /api/v1/plans/select-plan
**Purpose**: Select Plan

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `SelectPlanRequest`
    - `plan_id` (integer): Plan Id (Required)
    - `start_date` (any): Start Date (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### GET /api/v1/execution/today
**Purpose**: Get Today

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_TodaysHabitResponse__`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### POST /api/v1/execution/habit/complete
**Purpose**: Complete Habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `LogCompletionRequest`
    - `habit_id` (integer): Habit Id (Required)
    - `note` (any): Note (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_LogResponse_`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any
- **422**: Validation Error
  - Returns `HTTPValidationError`
    - `detail`: array

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### GET /api/v1/stats/profile
**Purpose**: Get Profile

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_UserStatResponse_`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### POST /api/v1/stats/process-day
**Purpose**: Process Day

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_Dict_str__Any__`
    - `success`: boolean
    - `data`: any
    - `message`: string
    - `meta`: any

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: Yes)*

---

### GET /
**Purpose**: Root

#### Request
- **Auth Required**: No
- **Body Schema**: None

#### Response
- **200**: Successful Response

#### Business Logic
*(Dynamic logic analysis inferred from test executions)*

#### Database Impact
*(DB impacts inferred from test executions)*

#### Validation Rules
*(Constraints derived from Pydantic schemas)*

#### Edge Cases
*(Tested edge cases)*

#### Security
*(Auth Required: No)*

---
