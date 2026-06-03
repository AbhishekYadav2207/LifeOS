# Endpoint Coverage & Test Report
Generated: 2026-06-03T13:24:57.649682

This report lists the status of every automated endpoint and scenario test.

## Execution Metrics
* **Total Tests Executed**: 21
* **Passed Tests**: 21
* **Failed Tests**: 0
* **Pass Rate**: 100.0%

## Detailed Test Logs
| Test Case (NodeID) | Outcome | Duration (s) | Error Details |
|---|---|---|---|
| `tests/test_activation.py::test_plan_activation_boundaries` | **PASSED** | 3.728 | None |
| `tests/test_auth.py::test_user_registration_and_login` | **PASSED** | 1.695 | None |
| `tests/test_concurrency.py::test_habit_completion_race` | **PASSED** | 4.610 | None |
| `tests/test_concurrency.py::test_plan_activation_race` | **PASSED** | 3.856 | None |
| `tests/test_concurrency.py::test_duplicate_habit_creation_race` | **PASSED** | 3.574 | None |
| `tests/test_execution.py::test_execution_lifecycle_and_rules` | **PASSED** | 3.774 | None |
| `tests/test_habits.py::test_habit_crud_and_ownership` | **PASSED** | 3.645 | None |
| `tests/test_integrity.py::test_database_integrity_rules` | **PASSED** | 0.244 | None |
| `tests/test_negative.py::test_authentication_negative` | **PASSED** | 0.005 | None |
| `tests/test_negative.py::test_authorization_negative` | **PASSED** | 3.298 | None |
| `tests/test_negative.py::test_validation_negative` | **PASSED** | 1.391 | None |
| `tests/test_negative.py::test_business_rules_negative` | **PASSED** | 1.747 | None |
| `tests/test_plans.py::test_plan_crud_and_validation` | **PASSED** | 2.665 | None |
| `tests/test_progression_v2.py::test_habit_difficulty_coefficients` | **PASSED** | 1.389 | None |
| `tests/test_progression_v2.py::test_v2_habit_completion_and_snapshots` | **PASSED** | 2.667 | None |
| `tests/test_progression_v2.py::test_dynamic_daily_xp_cap` | **PASSED** | 2.992 | None |
| `tests/test_progression_v2.py::test_recovery_token_source` | **PASSED** | 2.995 | None |
| `tests/test_progression_v2.py::test_burnout_detection_event` | **PASSED** | 6.507 | None |
| `tests/test_progression_v2.py::test_prestige_system` | **PASSED** | 1.581 | None |
| `tests/test_progression_v2.py::test_habit_dependency_cycles` | **PASSED** | 2.838 | None |
| `tests/test_stats.py::test_stats_streaks_and_ranks` | **PASSED** | 6.127 | None |
