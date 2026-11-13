"""Per-user fixed-window limit for FastAPI routes that spend a paid LLM call.

Cost control only (the product is free). In-memory, per process — the same
trade-off as the Express aiUserRateLimit. Use as a route dependency placed
after get_current_user:

    current_user: User = Depends(llm_rate_limit)
"""
import os
import threading
import time
from typing import Callable, Dict, Tuple

from fastapi import Depends, HTTPException

from server.core.security import get_current_user
from server.models.user import User

WINDOW_SECONDS = 60
_MAX_TRACKED_USERS = 5000

_lock = threading.Lock()
_buckets: Dict[str, Tuple[int, float]] = {}  # user id -> (count, reset_at)

# Overridable in tests.
_now: Callable[[], float] = time.monotonic


def _limit() -> int:
    try:
        value = int(os.getenv("RATE_LIMIT_LLM_PER_USER", "10"))
    except ValueError:
        return 10
    return value if value >= 1 else 10


def check_llm_rate_limit(user_id: object) -> None:
    """Raise 429 once the user exceeds the per-minute LLM budget."""
    key = str(user_id)
    limit = _limit()
    t = _now()
    with _lock:
        if len(_buckets) > _MAX_TRACKED_USERS:
            for k in [k for k, (_, reset) in _buckets.items() if t >= reset]:
                del _buckets[k]
        count, reset_at = _buckets.get(key, (0, t + WINDOW_SECONDS))
        if t >= reset_at:
            count, reset_at = 0, t + WINDOW_SECONDS
        if count >= limit:
            retry = max(1, int(reset_at - t) + 1)
            raise HTTPException(
                status_code=429,
                detail="Too many AI requests. Try again shortly.",
                headers={"Retry-After": str(retry)},
            )
        _buckets[key] = (count + 1, reset_at)


def reset_llm_rate_limit() -> None:
    with _lock:
        _buckets.clear()


def llm_rate_limit(current_user: User = Depends(get_current_user)) -> User:
    check_llm_rate_limit(current_user.id)
    return current_user
