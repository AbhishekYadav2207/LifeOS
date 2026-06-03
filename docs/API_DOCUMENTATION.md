# LifeOS V1 — API Documentation

## 1. System Overview
LifeOS V1 Backend Architecture. The API enables clients to interact with habit tracking, scoring, daily logs, and stats tracking. High-level flow involves Plan creation, execution logging, stats tracking and scoring.

## 2. API Summary Table

| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | /api/v1/auth/register | Register | No |
| POST | /api/v1/auth/login | Login | No |
| GET | /api/v1/plans/public | List public plans | No |
| GET | /api/v1/plans/mine | List my plans | Yes |
| POST | /api/v1/plans/ | Create a new plan | Yes |
| PUT | /api/v1/plans/{plan_id} | Update a plan | Yes |
| DELETE | /api/v1/plans/{plan_id} | Delete a plan | Yes |
| POST | /api/v1/plans/{plan_id}/activate | Activate a plan for the current user | Yes |
| GET | /api/v1/plans/{plan_id}/habits | Get habits for a specific plan | No |
| GET | /api/v1/habits/public | List public habits | No |
| GET | /api/v1/habits/mine | List my habits | Yes |
| POST | /api/v1/habits/ | Create a new habit | Yes |
| PUT | /api/v1/habits/{habit_id} | Update a habit | Yes |
| DELETE | /api/v1/habits/{habit_id} | Delete a habit | Yes |
| GET | /api/v1/today/ | Get Today | Yes |
| POST | /api/v1/today/habit/complete | Complete Habit | Yes |
| POST | /api/v1/today/process | Process Day | Yes |
| GET | /api/v1/stats/profile | Get Profile | Yes |
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

### GET /api/v1/plans/public
**Purpose**: List public plans

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

### GET /api/v1/plans/mine
**Purpose**: List my plans

#### Request
- **Auth Required**: Yes
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
*(Auth Required: Yes)*

---

### POST /api/v1/plans/
**Purpose**: Create a new plan

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `PlanCreate`
    - `name` (string): Name (Required)
    - `is_public` (boolean): Is Public (Optional)
    - `difficulty` (string): Difficulty (Required)
    - `habits` (array): Habits (Optional)

#### Response
- **201**: Successful Response
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

### PUT /api/v1/plans/{plan_id}
**Purpose**: Update a plan

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

### DELETE /api/v1/plans/{plan_id}
**Purpose**: Delete a plan

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

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

### POST /api/v1/plans/{plan_id}/activate
**Purpose**: Activate a plan for the current user

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

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

### GET /api/v1/plans/{plan_id}/habits
**Purpose**: Get habits for a specific plan

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

### GET /api/v1/habits/public
**Purpose**: List public habits

#### Request
- **Auth Required**: No
- **Body Schema**: None
- **Query Parameters**:
  - `category` (any) (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__`
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

### GET /api/v1/habits/mine
**Purpose**: List my habits

#### Request
- **Auth Required**: Yes
- **Body Schema**: None
- **Query Parameters**:
  - `category` (any) (Optional)

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_List_HabitResponse__`
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

### POST /api/v1/habits/
**Purpose**: Create a new habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `HabitCreate`
    - `name` (string): Name (Required)
    - `category` (any):  (Required)
    - `difficulty` (string): Difficulty (Required)
    - `base_score` (integer): Base Score (Optional)
    - `is_public` (boolean): Is Public (Optional)

#### Response
- **201**: Successful Response
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

### PUT /api/v1/habits/{habit_id}
**Purpose**: Update a habit

#### Request
- **Auth Required**: Yes
- **Body Schema**:
  - Model: `HabitCreate`
    - `name` (string): Name (Required)
    - `category` (any):  (Required)
    - `difficulty` (string): Difficulty (Required)
    - `base_score` (integer): Base Score (Optional)
    - `is_public` (boolean): Is Public (Optional)

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

### DELETE /api/v1/habits/{habit_id}
**Purpose**: Delete a habit

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

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

### GET /api/v1/today/
**Purpose**: Get Today

#### Request
- **Auth Required**: Yes
- **Body Schema**: None

#### Response
- **200**: Successful Response
  - Returns `BaseResponse_TodayResponse_`
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

### POST /api/v1/today/habit/complete
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

### POST /api/v1/today/process
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
