# System Features & Business Rules

## 1. User & Authentication System
* **Registration**: Allows users to register with an email and password. Passwords are securely hashed using BCrypt.
* **Timezone Config**: Users can provide a timezone (e.g. `"Asia/Kolkata"`, `"America/New_York"`) during registration. It defaults to `"UTC"` if omitted. Timezones are critical for determining local day boundaries.
* **Authentication**: Employs standard JWT authentication. Logins issue a Bearer access token valid for 30 minutes.

## 2. Habits & Plans Configuration
* **Habit Definition**: Habits are defined by:
  * `name`: Unique per creator.
  * `category`: Categorization tag.
  * `difficulty`: Difficulty level (`easy`, `medium`, `hard`).
  * `base_score`: Defaults to `10`.
  * `is_public`: Public habits can be included in any user's plan. Private habits are only visible to their creator.
* **Plan Composition**: Plans are collections of habits. Each mapping (`PlanHabit`) has:
  * `start_time` and `end_time`: Execution windows (optional).
  * `day_config`: Specifies scheduling filters (`everyday`, `weekdays`, `weekends`).
* **Active User Plan**:
  * Users select and activate a plan via `POST /api/v1/plans/{plan_id}/activate`.
  * Activation takes effect **today** (setting `start_date = local_today` and deactivating any old plan with `end_date = local_today`).
  * This guarantees that only one plan is active for a user on any date.

## 3. Daily Execution Logs
* **Initialization**: The first call to `GET /api/v1/today/` on a given date initializes the user's daily tracker.
* **Schedule Filtering**: The initialization checks the local day of the week:
  * If `day_config` is `"weekdays"` and today is Saturday/Sunday, the habit is excluded.
  * If `day_config` is `"weekends"` and today is Monday-Friday, the habit is excluded.
* **Pending Status**: All scheduled habits start as `"pending"` with `awarded_points = 0`.
* **Stability**: Log entries store snapshots of `snapshot_base_score` and habit name. Changing the habit's definition in the catalog does not affect historical logs.

## 4. Scoring Logic Matrix
Points are awarded and penalized based on completion status:

| Status | Code Condition | Points Awarded | Notes |
|---|---|---|---|
| **Completed (On-time)** | Completed before `end_time` | `+ base_score` | Default behavior if no `end_time` is set |
| **Completed (Late)** | Completed after `end_time` | `+ (base_score // 2)` | Marks `late_flag = True` |
| **Missed** | Uncompleted at daily process | `- (base_score // 2)` | Marks `status = "missed"` |

* **Daily Points Floor**: Points cannot drop below 0 at the daily summary level. The daily sum of awarded/penalized points is applied with `max(0, current_points + day_change)`.

## 5. Streak & Progression Engine
* **Streak Calculation**:
  * **Increment**: Current streak increases by `1` if **all** scheduled habits for a processed day are completed (`"done"`), and at least one habit was scheduled.
  * **Reset**: Current streak resets to `0` if **any** scheduled habit is missed (`"missed"`).
  * **Neutral**: If a processed day had no habits scheduled, it is a no-op (the streak is neither reset nor incremented).
  * **Max Streak**: Updated whenever the current streak exceeds the previously recorded max streak.
* **Rank System**: User rank is dynamically derived from total points:
  * `< 50`: `"Beginner"`
  * `< 150`: `"Starter"`
  * `< 300`: `"Rising"`
  * `< 500`: `"Consistent"`
  * `< 800`: `"Focused"`
  * `< 1200`: `"Disciplined"`
  * `< 1800`: `"Advanced"`
  * `< 2500`: `"Elite"`
  * `>= 2500`: `"Master"`

