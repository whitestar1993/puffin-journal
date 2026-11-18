from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.config import get_settings


def today(zone: ZoneInfo | None = None, now: datetime | None = None) -> date:
    """'Today' in the configured timezone (TZ env), not the server's UTC clock."""
    zone = zone or get_settings().zone
    now = now or datetime.now(timezone.utc)
    return now.astimezone(zone).date()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
