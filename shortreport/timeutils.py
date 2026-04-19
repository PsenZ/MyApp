from datetime import datetime
from zoneinfo import ZoneInfo


SYDNEY_TZ = ZoneInfo("Australia/Sydney")
US_EASTERN_TZ = ZoneInfo("America/New_York")


def now_sydney() -> datetime:
    return datetime.now(tz=SYDNEY_TZ)


def now_us_eastern() -> datetime:
    return datetime.now(tz=US_EASTERN_TZ)


def within_send_window(now_dt: datetime, hour: int, minute: int, window_minutes: int) -> bool:
    target = now_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return abs((now_dt - target).total_seconds()) <= window_minutes * 60


def is_regular_us_market_hours(now_dt_et: datetime) -> bool:
    if now_dt_et.weekday() >= 5:
        return False
    minutes = now_dt_et.hour * 60 + now_dt_et.minute
    return 9 * 60 + 30 <= minutes <= 16 * 60
