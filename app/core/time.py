from datetime import datetime, timezone

def get_current_time() -> datetime:
    """Returns the current UTC datetime. Useful for isolation and testing."""
    return datetime.now(timezone.utc)
