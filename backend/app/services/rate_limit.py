# app/services/rate_limit.py
"""Lightweight in-process rate limiting for abuse-sensitive endpoints.

A sliding-window counter keyed on (scope, client IP). This deliberately uses
no external store: it protects a single process against brute-force and AI-cost
abuse with zero new infrastructure.

Limitations (documented on purpose):
  * State is per-process. With multiple uvicorn workers each worker keeps its
    own window, so the effective limit is roughly (limit x workers). For a
    hard global limit, put a reverse proxy / API gateway limit in front, or
    swap the backing store for Redis.
  * It trusts the first X-Forwarded-For hop when present, so it must only sit
    behind a proxy you control.

Use RateLimiter as a FastAPI dependency; call reset_all() between tests.
"""

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.config import settings

_buckets: Dict[str, Deque[float]] = defaultdict(deque)
_lock = Lock()


def reset_all() -> None:
    """Clear every window — used by tests to isolate cases."""
    with _lock:
        _buckets.clear()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """FastAPI dependency that allows at most `limit` requests per
    `window_seconds` for each client IP within a named scope."""

    def __init__(self, scope: str, limit: int, window_seconds: int):
        self.scope = scope
        self.limit = limit
        self.window = window_seconds

    def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        key = f"{self.scope}:{_client_ip(request)}"
        now = time.monotonic()
        cutoff = now - self.window
        with _lock:
            bucket = _buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, int(bucket[0] + self.window - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down and try again shortly.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
