"""Small in-memory sliding-window rate limiter.

Good enough for a single process (development, one Uvicorn worker). Behind several
workers or machines, replace it with a shared store such as Redis.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError

_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def reset() -> None:
    with _lock:
        _hits.clear()


def rate_limit(name: str, limit: int, window_seconds: int):
    """FastAPI dependency factory: at most `limit` calls per `window_seconds` per client."""

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        client = request.client.host if request.client else "unknown"
        key = f"{name}:{client}"
        now = time.monotonic()
        with _lock:
            q = _hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                raise AppError(429, "RATE_LIMITED", "Too many requests. Please wait a moment and try again.")
            q.append(now)

    return dependency
