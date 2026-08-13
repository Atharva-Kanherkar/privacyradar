import pytest

pytestmark = pytest.mark.integration


def test_redis_ping_when_configured(redis_url: str) -> None:
    import redis as redis_lib

    client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=1)
    assert client.ping() is True
