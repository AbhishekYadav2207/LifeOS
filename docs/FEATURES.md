# Features

## User System
- **Registration**: Allows signing up via Email/Password. Secures data using BCrypt.
- **Login**: Employs standard JWT authentication with configurable expiration (Default: 30 minutes). Provides session security across all execution behaviors.
- **Timezone Aware**: Collects users' timezones upon sign-up to precisely frame their "days."

## Plan & Habit Interface
- **Habit Catalog**: Independent definition of foundational tasks, featuring custom difficulty, categorization, and base scoring logic rules.
- **Plans**: Aggregate collections of behaviors mapping dynamic subsets of the habit catalog. Provides configuration like Time Windows.
- **User Plans Execution Mapping**: Activating a plan affects future executions. It guarantees backwards-stability on logging history.

## Scoring System
Core scoring matrix tracks adherence intelligently:
- **Completed**: Points awarded natively to Habit Base Value at 100%.
- **Late**: Detects out-of-bounds inputs heuristics via `late_flag`. Applies a 50% static penalty on gains natively.
- **Missed**: Incurs negative drops automatically resolving open requests.

## Rank Structure
Global 9-tier system rewarding long-term streaks and adherence scale:
* Beginner (0-50), Starter (50-150), Rising (150-300), Consistent (300-500), Focused (500-800), Disciplined (800-1200), Advanced (1200-1800), Elite (1800-2500), Master (2500+).
