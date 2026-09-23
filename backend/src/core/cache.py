from functools import lru_cache

from redis.asyncio import ConnectionPool, Redis

from src.core.config import get_settings


class CacheClient:
    """Thin wrapper around the Redis connection used for session state,
    rate limiting, and short-lived agent memory.

    Route/domain code goes through this rather than importing `redis`
    directly, so pooling and key conventions live in one place.
    """

    def __init__(self, redis_url: str) -> None:
        self._pool = ConnectionPool.from_url(redis_url, decode_responses=True)
        self._redis = Redis(connection_pool=self._pool)

    @property
    def redis(self) -> Redis:
        return self._redis

    async def get(self, key: str) -> str | None:
        # redis-py's stubs type every reply as `bytes | str | None` regardless
        # of `decode_responses` (that flag isn't reflected in the type), but
        # it's set True above, so this is always `str | None` at runtime.
        value = await self._redis.get(key)
        assert value is None or isinstance(value, str)
        return value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        """Atomically increment `key`, setting its TTL on first creation.

        Used for fixed-window rate limiting: the caller compares the
        returned count against its limit.
        """
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            count, _ = await pipe.execute()
        return count

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def session_key(student_id: str) -> str:
        return f"session:{student_id}"

    @staticmethod
    def rate_limit_key(scope: str, student_id: str) -> str:
        return f"rate_limit:{scope}:{student_id}"


@lru_cache
def get_cache_client() -> CacheClient:
    return CacheClient(get_settings().redis_url)
