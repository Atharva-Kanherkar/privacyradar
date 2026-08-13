import pytest

pytestmark = pytest.mark.integration


def test_redis_ping_when_configured(redis_url: str) -> None:
    import redis as redis_lib

    client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=1)
    assert client.ping() is True


def test_arq_enqueue_fetch_due_job_roundtrip(redis_url: str) -> None:
    import asyncio

    from arq import create_pool
    from arq.connections import RedisSettings

    async def _run() -> None:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        job = await pool.enqueue_job("fetch_due_job")
        assert job is not None
        await pool.aclose()

    asyncio.run(_run())
