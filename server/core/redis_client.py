import os
import json
import logging
import redis
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _pool, _client
    if _client is not None:
        return _client
    try:
        _pool = redis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _client = redis.Redis(connection_pool=_pool)
        _client.ping()
        logger.info("Redis connected successfully")
        return _client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"Redis unavailable, using fallback: {e}")
        return _NullRedis()


class _NullRedis:
    def get(self, *a, **kw):
        return None

    def set(self, *a, **kw):
        return True

    def setex(self, *a, **kw):
        return True

    def delete(self, *a, **kw):
        return 0

    def lpush(self, *a, **kw):
        return 0

    def brpop(self, *a, **kw):
        return None

    def rpush(self, *a, **kw):
        return 0

    def llen(self, *a, **kw):
        return 0

    def lrange(self, *a, **kw):
        return []

    def ping(self):
        return False

    def exists(self, *a, **kw):
        return 0

    def expire(self, *a, **kw):
        return False

    def incr(self, *a, **kw):
        return 0

    def keys(self, *a, **kw):
        return []

    def pipeline(self, *a, **kw):
        return self

    def execute(self, *a, **kw):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass
