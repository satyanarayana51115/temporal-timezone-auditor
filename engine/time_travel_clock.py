import re
from datetime import datetime
from freezegun import freeze_time

ISO_TZ_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


class TemporalAuditorEngine:
    """
    Controls deterministic time-travel states and validates ISO-8601
    timezone awareness across API payloads.
    """

    @staticmethod
    def travel_to(iso_timestamp: str):
        """Context manager to freeze system clock at an exact UTC instant."""
        return freeze_time(iso_timestamp)

    @staticmethod
    def has_valid_tz_offset(timestamp_str: str) -> bool:
        """Returns True only if timestamp includes explicit UTC 'Z' or +/-HH:MM offset."""
        if not timestamp_str:
            return False
        return bool(ISO_TZ_PATTERN.match(timestamp_str))

    @staticmethod
    def verify_iso_parseable(timestamp_str: str) -> bool:
        """Validates strict ISO-8601 parsing including Leap Year Feb 29 dates."""
        try:
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False