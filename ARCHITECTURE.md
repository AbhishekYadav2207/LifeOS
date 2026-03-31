# System Architecture

## Overview
LifeOS Backend utilizes FastAPI with asynchronous dependency injection routed purely into independent business service logics.

## Data Lifecycle 
1. **Plans Engine System**: `PlanHabit` maps a `Habit` to a `Plan`. `UserPlan` maps the user to their desired plan. Note that modifications to a User's Plan (or new subscriptions) apply on their *next day*. 
2. **Immutable Snapshot Logs**: `DailyLogs` trace executed behaviors daily. They pull habit strings and scoring parameters statically — so if a `Habit` changes severity internally, past aggregated statistics stay unchanged.
3. **Execution Service**: Initial request to `/today` calculates local bounds per user and generates native "Pending" empty logs against the active User Plan.
4. **Scoring Service Engine**: At midnight or forcefully via `/process-day`, the unhandled "Pending" logs drop into failures logic (-50% base), updating `UserStat` records incrementally for streak limits securely.
