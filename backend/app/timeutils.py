"""Date/time helpers. Stored timestamps are UTC; 'today' uses the shop timezone."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def shop_today(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def local_day_bounds_utc(day: date, tz_name: str) -> tuple[str, str]:
    """UTC ISO range [start, end) covering one calendar day in the shop timezone."""
    start = datetime.combine(day, time.min, tzinfo=ZoneInfo(tz_name))
    end = start + timedelta(days=1)
    return (
        start.astimezone(timezone.utc).isoformat(timespec="seconds"),
        end.astimezone(timezone.utc).isoformat(timespec="seconds"),
    )
