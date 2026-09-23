import uuid

import pytest

from src.core.cache import CacheClient
from src.core.config import get_settings


@pytest.fixture
async def cache() -> CacheClient:
    client = CacheClient(get_settings().redis_url)
    yield client
    await client.close()


async def test_set_get_delete_roundtrip(cache: CacheClient) -> None:
    key = f"test:{uuid.uuid4()}"
    await cache.set(key, "value", ttl_seconds=30)

    assert await cache.get(key) == "value"

    await cache.delete(key)
    assert await cache.get(key) is None


async def test_incr_with_ttl_counts_and_expires(cache: CacheClient) -> None:
    key = CacheClient.rate_limit_key("test-scope", str(uuid.uuid4()))

    assert await cache.incr_with_ttl(key, ttl_seconds=60) == 1
    assert await cache.incr_with_ttl(key, ttl_seconds=60) == 2

    ttl = await cache.redis.ttl(key)
    assert 0 < ttl <= 60

    await cache.delete(key)
