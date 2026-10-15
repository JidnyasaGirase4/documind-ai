from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime. All timestamps are stored in UTC and serialised with a trailing Z."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
