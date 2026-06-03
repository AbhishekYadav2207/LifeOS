# API Documentation

All API routes are prefixed with `/api/v1`.

## Auth Routes
* `POST /api/v1/auth/register`: Signs up a user given a JSON of `{"email", "password", "timezone"}`. Timezone defaults to `"UTC"` if not provided.
* `POST /api/v1/auth/login`: Issues a JWT 30-minute access token.

## Habit Routes
* `GET /api/v1/habits/public`: Lists public habits. Supports filtering by `category` query parameter.
* `GET /api/v1/habits/mine`: Lists user-specific habits created by the current user.
* `POST /api/v1/habits/`: Creates a new habit.
* `PUT /api/v1/habits/{habit_id}`: Updates a habit. Only accessible by the creator of the habit.
* `DELETE /api/v1/habits/{habit_id}`: Deletes a habit. Only accessible by the creator of the habit.

## Plan Routes
* `GET /api/v1/plans/`: Lists all public plans.
* `GET /api/v1/plans/mine`: Lists all plans created by the current user.
* `POST /api/v1/plans/`: Creates a new plan mapped to a list of habit IDs (with start_time, end_time, and day_config).
* `PUT /api/v1/plans/{plan_id}`: Updates a plan. Only accessible by the creator of the plan.
* `DELETE /api/v1/plans/{plan_id}`: Deletes a plan. Only accessible by the creator of the plan.
* `POST /api/v1/plans/{plan_id}/activate`: Deactivates all existing active plans for the user and activates the given plan starting today (`start_date = local_today`).
* `GET /api/v1/plans/{plan_id}/habits`: Lists habits associated with a specific plan (returns `PlanHabitTimelineResponse` with timing metadata).

## Execution Routes
* `GET /api/v1/today/`: Fetches or initializes tracking layout (pending daily logs) natively mapped to the active `UserPlan` for the user's local date. Also automatically executes a backfill processing for any unprocessed days prior to today (up to 7 days).
* `POST /api/v1/today/habit/complete`: Updates a pending daily log instance to "done", assigning its `late_flag` based on whether the current local time is past the habit's `end_time` configuration.

## Stat Routes
* `GET /api/v1/stats/profile`: Returns aggregated metrics: total points, current streak, max streak, and rank.
* `POST /api/v1/today/process`: Manually triggers daily processing for today's logs, marking remaining pending logs as missed, applying penalties, and updating stats. (Streaks increment if all tasks completed and at least one habit was scheduled; streaks reset if any habit is missed).

