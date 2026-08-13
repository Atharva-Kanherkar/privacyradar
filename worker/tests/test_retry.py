from datetime import UTC, datetime, timedelta
from random import Random

from privacyradar.retry import (
    BACKOFF_CAP_SECONDS,
    MAX_RETRIES_PER_WINDOW,
    backoff_seconds,
    idempotency_key,
    is_retryable,
    next_due_at,
)


def test_http_429_is_retryable_http_4xx_is_not() -> None:
    assert is_retryable("http_429")
    assert is_retryable("timeout")
    assert is_retryable("http_5xx")
    assert is_retryable("network")
    assert not is_retryable("http_4xx")
    assert not is_retryable("ssrf")
    assert not is_retryable("robots")
    assert not is_retryable("oversize")
    assert not is_retryable("moved")
    assert not is_retryable(None)


def test_retry_backoff_monotonic_and_capped() -> None:
    rng = Random(0)
    delays = [backoff_seconds(n, rng=Random(0)) for n in range(1, 8)]
    assert delays[0] == backoff_seconds(1, rng=Random(0))
    assert delays[1] > delays[0]
    assert delays[2] > delays[1]
    assert delays[-1] <= BACKOFF_CAP_SECONDS * 1.2
    jittered = backoff_seconds(1, rng=rng)
    assert 48 <= jittered <= 72


def test_retry_budget_stops_at_five() -> None:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    rng = Random(0)
    fourth = next_due_at(now, "timeout", 4, rng=rng)
    fifth = next_due_at(now, "timeout", MAX_RETRIES_PER_WINDOW, rng=Random(0))
    assert fourth < now + timedelta(hours=6)
    assert fifth == now + timedelta(hours=6)
    assert next_due_at(now, "ssrf", 1, rng=Random(0)) == now + timedelta(hours=6)
    assert next_due_at(now, None, 0, rng=Random(0)) == now + timedelta(hours=6)


def test_idempotency_key_stable_within_hour() -> None:
    source = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    first = datetime(2026, 1, 15, 12, 5, 1, tzinfo=UTC)
    second = datetime(2026, 1, 15, 12, 59, 59, tzinfo=UTC)
    later = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    assert idempotency_key(source, first) == idempotency_key(source, second)
    assert idempotency_key(source, first) == (
        f"fetch:{source}:2026-01-15T12:00:00Z"
    )
    assert idempotency_key(source, later) != idempotency_key(source, first)
