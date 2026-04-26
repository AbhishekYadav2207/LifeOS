from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

def get_current_time(tz_name: str = "UTC") -> datetime:
    """Returns the current datetime in the given timezone."""
    tz = ZoneInfo(tz_name)
    return datetime.now(tz)

def get_local_today(tz_name: str = "UTC") -> date:
    """Returns today's date in the user's timezone."""
    return get_current_time(tz_name).date()
