"""Retry budgets and idempotency keys for per-source fetch jobs."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

RETRYABLE_ERROR_CODES = frozenset({"timeout", "http_5xx", "http_429", "network"})
MAX_RETRIES_PER_WINDOW = 5
BACKOFF_BASE_SECONDS = 60
BACKOFF_FACTOR = 2
BACKOFF_CAP_SECONDS = 6 * 3600
JITTER_RATIO = 0.2
LEASE_SECONDS = 120
SUCCESS_INTERVAL_SECONDS = 6 * 3600
HTTP_CONCURRENCY = 8
PER_DOMAIN_CONCURRENCY = 1
BROWSER_CONCURRENCY = 1


def is_retryable(error_code: str | None) -> bool:
    return error_code in RETRYABLE_ERROR_CODES


def backoff_seconds(attempt_no: int, *, rng: random.Random) -> float:
    if attempt_no < 1:
        attempt_no = 1
    raw = min(
        BACKOFF_CAP_SECONDS,
        BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (attempt_no - 1)),
    )
    jitter = 1 + rng.uniform(-JITTER_RATIO, JITTER_RATIO)
    return float(raw) * jitter


def next_due_at(
    now: datetime,
    error_code: str | None,
    attempt_no: int,
    *,
    rng: random.Random,
) -> datetime:
    """Schedule the next fetch. Exhausted or non-retryable failures wait a full window."""
    if error_code is None:
        return now + timedelta(seconds=SUCCESS_INTERVAL_SECONDS)
    if not is_retryable(error_code) or attempt_no >= MAX_RETRIES_PER_WINDOW:
        return now + timedelta(seconds=SUCCESS_INTERVAL_SECONDS)
    return now + timedelta(seconds=backoff_seconds(attempt_no, rng=rng))


def idempotency_key(source_id: str, due_at: datetime) -> str:
    hour = due_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    stamp = hour.strftime("%Y-%m-%dT%H:00:00Z")
    return f"fetch:{source_id}:{stamp}"
