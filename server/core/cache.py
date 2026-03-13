import json
import hashlib
import logging
import functools
from typing import Optional, Any

from server.core.redis_client import get_redis

logger = logging.getLogger(__name__)

PREFIX = "fc:"
DEFAULT_TTL = 300


def cache_key(*parts: str) -> str:
    return PREFIX + ":".join(str(p) for p in parts)


def cache_get(key: str) -> Optional[Any]:
    try:
        r = get_redis()
        val = r.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.debug(f"Cache get failed for {key}: {e}")
    return None


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    try:
        r = get_redis()
        r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug(f"Cache set failed for {key}: {e}")
    return False


def cache_delete(key: str) -> bool:
    try:
        r = get_redis()
        r.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache delete failed for {key}: {e}")
    return False


def cache_invalidate_pattern(pattern: str) -> int:
    try:
        r = get_redis()
        keys = r.keys(PREFIX + pattern)
        if keys:
            return r.delete(*keys)
    except Exception as e:
        logger.debug(f"Cache invalidate failed for {pattern}: {e}")
    return 0


def cached(key_prefix: str, ttl: int = DEFAULT_TTL, company_scoped: bool = True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if company_scoped:
                company_id = kwargs.get("company_id") or (args[1] if len(args) > 1 else None)
                key = cache_key(key_prefix, str(company_id))
            else:
                key_parts = [key_prefix] + [str(a) for a in args[1:3]]
                key = cache_key(*key_parts)

            result = cache_get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
