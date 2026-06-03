# Endpoint Coverage & Test Report
Generated: 2026-06-03T09:38:17.104852

This report lists the status of every automated endpoint and scenario test.

## Execution Metrics
* **Total Tests Executed**: 14
* **Passed Tests**: 14
* **Failed Tests**: 0
* **Pass Rate**: 100.0%

## Detailed Test Logs
| Test Case (NodeID) | Outcome | Duration (s) | Error Details |
|---|---|---|---|
| `tests/test_activation.py::test_plan_activation_boundaries` | **PASSED** | 1.110 | None |
| `tests/test_auth.py::test_user_registration_and_login` | **PASSED** | 0.744 | None |
| `tests/test_concurrency.py::test_habit_completion_race` | **PASSED** | 1.823 | None |
| `tests/test_concurrency.py::test_plan_activation_race` | **PASSED** | 1.601 | None |
| `tests/test_concurrency.py::test_duplicate_habit_creation_race` | **PASSED** | 1.449 | None |
| `tests/test_execution.py::test_execution_lifecycle_and_rules` | **PASSED** | 0.668 | None |
| `tests/test_habits.py::test_habit_crud_and_ownership` | **PASSED** | 1.074 | None |
| `tests/test_integrity.py::test_database_integrity_rules` | **PASSED** | 0.007 | None |
| `tests/test_negative.py::test_authentication_negative` | **PASSED** | 0.003 | None |
| `tests/test_negative.py::test_authorization_negative` | **PASSED** | 1.009 | None |
| `tests/test_negative.py::test_validation_negative` | **PASSED** | 0.498 | None |
| `tests/test_negative.py::test_business_rules_negative` | **PASSED** | 0.634 | None |
| `tests/test_plans.py::test_plan_crud_and_validation` | **PASSED** | 0.595 | None |
| `tests/test_stats.py::test_stats_streaks_and_ranks` | **PASSED** | 0.809 | None |
