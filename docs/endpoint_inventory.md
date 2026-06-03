# Endpoint Inventory

| Method | Path | Auth Required | Request Model | Response Model | Summary |
|---|---|---|---|---|---|
| POST | /api/v1/auth/register | No | `UserCreate` | `BaseResponse_UserResponse_` | Register |
| POST | /api/v1/auth/login | No | `UserLogin` | `BaseResponse_TokenData_` | Login |
| GET | /api/v1/plans/habits | Yes | None | `BaseResponse_List_HabitResponse__` | List all habits |
| POST | /api/v1/plans/habits | Yes | `HabitCreate` | `BaseResponse_HabitResponse_` | Create a new habit |
| GET | /api/v1/plans/habits/public | No | None | `BaseResponse_List_HabitResponse__` | List public habits |
| GET | /api/v1/plans/habits/mine | Yes | None | `BaseResponse_List_HabitResponse__` | List my habits |
| PUT | /api/v1/plans/habits/{habit_id} | Yes | `HabitCreate` | `BaseResponse_HabitResponse_` | Update a habit |
| DELETE | /api/v1/plans/habits/{habit_id} | Yes | None | `BaseResponse` | Delete a habit |
| GET | /api/v1/plans/ | No | None | `BaseResponse_List_PlanResponse__` | List public plans |
| POST | /api/v1/plans/ | Yes | `PlanCreate` | `BaseResponse_PlanResponse_` | Create a new plan |
| GET | /api/v1/plans/mine | Yes | None | `BaseResponse_List_PlanResponse__` | List my plans |
| PUT | /api/v1/plans/{plan_id} | Yes | `PlanCreate` | `BaseResponse_PlanResponse_` | Update a plan |
| DELETE | /api/v1/plans/{plan_id} | Yes | None | `BaseResponse` | Delete a plan |
| POST | /api/v1/plans/{plan_id}/activate | Yes | None | `BaseResponse` | Activate a plan for the current user |
| GET | /api/v1/plans/{plan_id}/habits | Yes | None | `BaseResponse_List_PlanHabitTimelineResponse__` | Get habits for a specific plan |
| GET | /api/v1/execution/today | Yes | None | `BaseResponse_List_TodaysHabitResponse__` | Get Today |
| POST | /api/v1/execution/habit/complete | Yes | `LogCompletionRequest` | `BaseResponse_LogResponse_` | Complete Habit |
| GET | /api/v1/stats/profile | Yes | None | `BaseResponse_UserStatResponse_` | Get Profile |
| POST | /api/v1/stats/process-day | Yes | None | `BaseResponse_Dict_str__Any__` | Process Day |
| GET | / | No | None | None | Root |
