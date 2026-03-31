# API Documentation

## Auth Routes
* `POST /api/auth/register`: Signs up a user given a JSON of `{"email", "password", "timezone"}`.
* `POST /api/auth/login`: Issues a JWT 30-minute access token. 

## Plan and Habit Routes
* `GET /api/plans/`: List all public plans.
* `POST /api/plans/`: Creates a newly mapped plan with habit IDs.
* `POST /api/plans/select-plan`: Sets the active tracker map to begin starting tomorrow.
* `GET /api/plans/habits`: Lists base library.
* `POST /api/plans/habits`: Adds to the base library.

## Execution Routes
* `GET /api/execution/today`: Fetches tracking layout natively mapped to the active `UserPlan` and initializes immntable logs.
* `POST /api/execution/habit/complete`: Updates a pending DailyLog instance to "done", with optional string notes and assigns its `late_flag` based on timing heuristics.

## Stat Routes
* `GET /api/stats/profile`: Returns aggregated metrics: Points, streaks, max streaks, and Rank.
* `POST /api/stats/process-day`: Sweeps today's DailyLogs natively terminating "pending" assignments locally evaluating behavior drops correctly. Generates summarized feedback and scales streaks internally.
