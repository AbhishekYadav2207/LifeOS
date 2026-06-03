# Business Rules Discovery

This document captures the business rules, scoring metrics, streaks, validations, and edge cases discovered by reverse-engineering the codebase.

## 1. Ownership & Authorization Rules
* **Habit Ownership**: Habits can only be updated (`PUT /plans/habits/{id}`) or deleted (`DELETE /plans/habits/{id}`) by the user who created them (`created_by == current_user.id`).
* **Plan Ownership**: Private plans (`is_public == False`) can only be updated, deleted, viewed (`GET /plans/{id}/habits`), or activated by the user who created them. Public plans can be viewed or activated by any user.
* **Log Completion**: Users can only complete logs that belong to them (`user_id == current_user.id`).

## 2. Plan Activation Logic
* **Endpoint**: `POST /plans/{plan_id}/activate`
* **Behavior**:
  1. Deactivates all existing active plans for the user (`active = False`, and sets `end_date = local_today`).
  2. Creates a new `UserPlan` record with `active = True`, `start_date = local_today`, and `end_date = None`.
  3. Database constraint `uix_one_active_plan` guarantees that a user can have at most one active plan at any time.

## 3. Daily execution & Logging
* **Endpoint**: `GET /execution/today`
* **Behavior**:
  1. Determines the user's current date based on their `timezone` profile.
  2. Runs **Auto-Backfill**: Sweeps any unprocessed days from `last_processed_date` (or earliest log date) up to yesterday (limit 7 days). It calls `scoring_svc.process_day` for each missed day.
  3. Initializes today's logs: Fetches all `PlanHabit` mappings for the active plan.
  4. Filters habits by `day_config` weekdays/weekends:
     * If `day_config == "weekdays"` and today is Saturday/Sunday, the habit is skipped.
     * If `day_config == "weekends"` and today is Monday-Friday, the habit is skipped.
  5. Immutably inserts pending logs (`status = "pending"`, `awarded_points = 0`).

## 4. Habit Completion & Late Window Logic
* **Endpoint**: `POST /execution/habit/complete`
* **Behavior**:
  1. The task must have a status of `"pending"`.
  2. Computes the user's local current time.
  3. Compares the current local wall-clock time with the habit's `end_time` configuration.
  4. If `end_time` is configured and current time is past `end_time`, `late_flag` is set to `True`.
  5. **Scoring Penalty**:
     * Normal completion: user gets `snapshot_base_score` points.
     * Late completion: user gets `snapshot_base_score // 2` points (half, integer division).

## 5. Daily Processing & streak Logic
* **Endpoint**: `POST /stats/process-day` (or auto-triggered backfills)
* **Behavior**:
  1. Marks any remaining `"pending"` logs as `"missed"`.
  2. **Miss Penalty**: Missed tasks subtract half their base score (`awarded_points = - (log.snapshot_base_score // 2)`).
  3. Updates `UserStat` and `UserPlanStat` totals by summing the day's `awarded_points`.
  4. Points cannot fall below 0 (`max(0, points + total_score_change)`).
  5. **Streak Rules**:
     * If **any** task is missed: Current streak is reset to `0`.
     * If **all** tasks are completed (`status == "done"`) and the day has at least one task: Current streak increments by `1`.
     * If current streak exceeds max streak, max streak is updated.
     * If a day contains no logs (e.g. no habits scheduled), it is a no-op and does not affect the streak.

## 6. Rank Thresholds
User Rank is calculated from `total_points`:
* `< 50`: `"Beginner"`
* `< 150`: `"Starter"`
* `< 300`: `"Rising"`
* `< 500`: `"Consistent"`
* `< 800`: `"Focused"`
* `< 1200`: `"Disciplined"`
* `< 1800`: `"Advanced"`
* `< 2500`: `"Elite"`
* `>= 2500`: `"Master"`
