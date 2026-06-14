from __future__ import annotations

import warnings
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


FIXED_TIMEZONES = {
    "Asia/Calcutta": timezone(timedelta(hours=5, minutes=30), name="IST"),
    "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30), name="IST"),
    "UTC": timezone.utc,
}


def resolve_timezone(name: str) -> tzinfo:
    """Resolve an IANA timezone without requiring tzdata on Windows."""
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        fixed = FIXED_TIMEZONES.get(name)
        if fixed is not None:
            return fixed

        local_timezone = datetime.now().astimezone().tzinfo or timezone.utc
        warnings.warn(
            f"Timezone {name!r} is unavailable; using system timezone "
            f"{local_timezone} instead. Install tzdata for full IANA support.",
            RuntimeWarning,
            stacklevel=2,
        )
        return local_timezone


def now_in_timezone(name: str) -> datetime:
    return datetime.now(resolve_timezone(name))
