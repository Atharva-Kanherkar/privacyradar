"""Per-source fetch jobs with expiring row leases."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Any, cast
from urllib.parse import urlparse
from uuid import uuid4

from privacyradar.crawl import FetchResult
from privacyradar.fetch import fetch_policy_url
from privacyradar.hashing import NORMALIZER_VERSION
from privacyradar.observe import HEALTH_QUARANTINE_AFTER, _health_after_failure, observe_source
from privacyradar.render import with_render_fallback
from privacyradar.retry import (
    HTTP_CONCURRENCY,
    LEASE_SECONDS,
    MAX_RETRIES_PER_WINDOW,
    idempotency_key,
    is_retryable,
    next_due_at,
)
from privacyradar.settings import settings
from privacyradar.ssrf import registrable_domain

logger = logging.getLogger(__name__)

# Serializes claimers so per-domain/global caps cannot race across connections.
CLAIM_ADVISORY_LOCK_KEY = 8462016

QUARANTINE_REASON_BY_CODE = {
    "ssrf": "ssrf",
    "robots": "robots",
    "blocked": "blocked",
    "oversize": "oversize",
    "moved": "moved",
    "empty": "invalid_content",
    "short": "invalid_content",
    "wrong_type": "invalid_content",
    "normalize_failed": "invalid_content",
}


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    source: dict[str, Any]
    lease_token: str
    lease_expires_at: datetime


def _domain_from_url(url: str) -> str:
    hostname = urlparse(url).hostname or url
    return registrable_domain(hostname)


def _invoke_fetch(fetch_fn: Any, source: dict[str, Any]) -> FetchResult:
    url = str(source["url"])
    try:
        return cast(
            FetchResult,
            fetch_fn(
                url,
                etag=source.get("etag"),
                last_modified=source.get("last_modified"),
            ),
        )
    except TypeError:
        return cast(FetchResult, fetch_fn(url))


def schedule_due_sources(conn: Any, now: datetime) -> int:
    rows = conn.execute(
        """
        select id, due_at
        from policy_sources
        where enabled = true
          and health_status <> 'quarantined'
          and due_at <= %s
        """,
        (now,),
    ).fetchall()
    inserted = 0
    for row in rows:
        key = idempotency_key(str(row["id"]), row["due_at"])
        result = conn.execute(
            """
            insert into fetch_jobs (idempotency_key, source_id, status, run_after)
            values (%s, %s, 'pending', %s)
            on conflict (idempotency_key) do nothing
            returning id
            """,
            (key, row["id"], row["due_at"]),
        ).fetchone()
        if result is not None:
            inserted += 1
    logger.info(
        "jobs scheduled",
        extra={"jobs_scheduled": inserted, "due_sources": len(rows)},
    )
    return inserted


def _active_lease_count(conn: Any, now: datetime) -> int:
    row = conn.execute(
        """
        select count(*) as n
        from policy_sources
        where lease_expires_at is not null and lease_expires_at > %s
        """,
        (now,),
    ).fetchone()
    return int(row["n"] if row else 0)


def _leased_domains(conn: Any, now: datetime) -> set[str]:
    rows = conn.execute(
        """
        select url
        from policy_sources
        where lease_expires_at is not null and lease_expires_at > %s
        """,
        (now,),
    ).fetchall()
    return {_domain_from_url(str(row["url"])) for row in rows}


def claim_fetch_job(conn: Any, worker_id: str, now: datetime) -> ClaimedJob | None:
    conn.execute("select pg_advisory_xact_lock(%s)", (CLAIM_ADVISORY_LOCK_KEY,))
    if _active_lease_count(conn, now) >= HTTP_CONCURRENCY:
        return None
    leased_domains = _leased_domains(conn, now)
    candidates = conn.execute(
        """
        select
          j.id as job_id,
          s.id as source_id,
          s.url,
          s.kind,
          s.region,
          s.etag,
          s.last_modified,
          s.company_id,
          c.slug,
          c.name
        from fetch_jobs j
        join policy_sources s on s.id = j.source_id
        join companies c on c.id = s.company_id
        where (
            (
              j.status in ('pending', 'retryable_failed')
              and j.run_after <= %s
            )
            or (
              j.status = 'leased'
              and j.lease_expires_at is not null
              and j.lease_expires_at <= %s
            )
          )
          and s.enabled = true
          and s.health_status <> 'quarantined'
          and (s.lease_expires_at is null or s.lease_expires_at <= %s)
        order by j.run_after, j.created_at
        for update of j, s skip locked
        limit 24
        """,
        (now, now, now),
    ).fetchall()
    for row in candidates:
        domain = _domain_from_url(str(row["url"]))
        if domain in leased_domains:
            continue
        token = uuid4()
        expires = now + timedelta(seconds=LEASE_SECONDS)
        conn.execute(
            """
            update policy_sources
            set lease_owner = %s, lease_token = %s, lease_expires_at = %s
            where id = %s
            """,
            (worker_id, token, expires, row["source_id"]),
        )
        conn.execute(
            """
            update fetch_jobs
            set status = 'leased',
                lease_owner = %s,
                lease_token = %s,
                lease_expires_at = %s
            where id = %s
            """,
            (worker_id, token, expires, row["job_id"]),
        )
        logger.info(
            "job claimed",
            extra={
                "job_id": str(row["job_id"]),
                "source_id": str(row["source_id"]),
                "lease_age_ms": 0,
            },
        )
        return ClaimedJob(
            job_id=str(row["job_id"]),
            source={
                "source_id": str(row["source_id"]),
                "url": row["url"],
                "kind": row["kind"],
                "region": row["region"],
                "etag": row["etag"],
                "last_modified": row["last_modified"],
                "company_id": str(row["company_id"]),
                "slug": row["slug"],
                "name": row["name"],
            },
            lease_token=str(token),
            lease_expires_at=expires,
        )
    return None


def _quarantine_reason(error_code: str | None, consecutive: int) -> str | None:
    if consecutive >= HEALTH_QUARANTINE_AFTER:
        if error_code in QUARANTINE_REASON_BY_CODE:
            return QUARANTINE_REASON_BY_CODE[error_code]
        return "consecutive_failures"
    return None


def finish_job(
    conn: Any,
    *,
    job_id: str,
    source_id: str,
    observed_health: str,
    error_code: str | None,
    etag: str | None,
    last_modified: str | None,
    now: datetime,
    rng: Random,
) -> None:
    source = conn.execute(
        """
        select consecutive_failures, retry_count, current_snapshot_id
        from policy_sources where id = %s for update
        """,
        (source_id,),
    ).fetchone()
    if source is None:
        return
    job = conn.execute(
        "select attempt_no, status from fetch_jobs where id = %s for update",
        (job_id,),
    ).fetchone()
    if job is None or job["status"] != "leased":
        return
    attempt_no = int(job["attempt_no"] if job else 0) + 1
    retry_count = int(source["retry_count"] or 0)
    consecutive = int(source["consecutive_failures"] or 0)
    job_status = "succeeded"
    due_at = next_due_at(now, None, 0, rng=rng)
    next_retry = 0
    q_reason = None
    q_at = None

    if error_code is None and observed_health == "healthy":
        consecutive = 0
        next_retry = 0
        due_at = next_due_at(now, None, 0, rng=rng)
        job_status = "succeeded"
    elif is_retryable(error_code) and attempt_no < MAX_RETRIES_PER_WINDOW:
        job_status = "retryable_failed"
        next_retry = retry_count + 1
        due_at = next_due_at(now, error_code, attempt_no, rng=rng)
    else:
        next_retry = 0
        due_at = next_due_at(now, error_code, MAX_RETRIES_PER_WINDOW, rng=rng)
        if is_retryable(error_code):
            consecutive += 1
            observed_health = _health_after_failure(consecutive)
        q_reason = _quarantine_reason(error_code, consecutive)
        if observed_health == "quarantined" or q_reason:
            job_status = "quarantined"
            q_at = now
            if observed_health == "quarantined" and q_reason is None:
                q_reason = "consecutive_failures"

    conn.execute(
        """
        update fetch_jobs
        set status = %s,
            attempt_no = %s,
            finished_at = %s,
            error_code = %s,
            lease_owner = null,
            lease_token = null,
            lease_expires_at = null,
            run_after = %s
        where id = %s
        """,
        (job_status, attempt_no, now, error_code, due_at, job_id),
    )
    conn.execute(
        """
        update policy_sources
        set lease_owner = null,
            lease_token = null,
            lease_expires_at = null,
            retry_count = %s,
            due_at = %s,
            consecutive_failures = %s,
            health_status = %s,
            etag = coalesce(%s, etag),
            last_modified = coalesce(%s, last_modified),
            quarantine_reason = %s,
            quarantined_at = %s
        where id = %s
        """,
        (
            next_retry,
            due_at,
            consecutive,
            observed_health,
            etag,
            last_modified,
            q_reason,
            q_at,
            source_id,
        ),
    )


def run_claimed_job(
    conn: Any,
    claimed: ClaimedJob,
    *,
    fetch: Any = None,
    now: datetime | None = None,
    rng: Random | None = None,
) -> str:
    clock = now or datetime.now(UTC)
    fetch_fn = fetch if fetch is not None else fetch_policy_url
    source = claimed.source
    try:
        fetched: FetchResult = _invoke_fetch(fetch_fn, source)
        fetched = with_render_fallback(
            str(source["url"]),
            fetched,
            None,
            enabled=settings.playwright_fallback,
        )
        observed = observe_source(conn, source, fetched, clock=clock)
        error_code = observed.error_code
        health = observed.health_status
        message = observed.message
        etag = fetched.etag
        last_modified = fetched.last_modified
        http_status = fetched.status
        outcome = observed.outcome
    except Exception as exc:
        logger.info(
            "job poison",
            extra={
                "job_id": claimed.job_id,
                "source_id": source["source_id"],
                "error_type": type(exc).__name__,
            },
        )
        error_code = "network"
        health = "degraded"
        message = f"{source['slug']}: fetch failed (network)"
        etag = None
        last_modified = None
        http_status = 0
        outcome = "failed"
        conn.execute(
            """
            insert into source_attempts (
              id, source_id, started_at, finished_at, strategy, status,
              http_status, content_type, request_url, resolved_url, error_code,
              byte_count, normalizer_version
            )
            values (%s, %s, %s, %s, 'http', 'failed', 0, '', %s, %s, 'network', 0, %s)
            """,
            (
                str(uuid4()),
                source["source_id"],
                clock,
                clock,
                source["url"],
                source["url"],
                NORMALIZER_VERSION,
            ),
        )
        job_row = conn.execute(
            "select attempt_no from fetch_jobs where id = %s",
            (claimed.job_id,),
        ).fetchone()
        attempt_no = int(job_row["attempt_no"] if job_row else 0) + 1
        if attempt_no >= MAX_RETRIES_PER_WINDOW:
            conn.execute(
                """
                update policy_sources
                set consecutive_failures = %s,
                    health_status = 'quarantined'
                where id = %s
                """,
                (HEALTH_QUARANTINE_AFTER, source["source_id"]),
            )
            health = "quarantined"
            finish_job(
                conn,
                job_id=claimed.job_id,
                source_id=str(source["source_id"]),
                observed_health=health,
                error_code=error_code,
                etag=etag,
                last_modified=last_modified,
                now=clock,
                rng=rng or Random(0),
            )
            conn.execute(
                """
                update policy_sources
                set quarantine_reason = 'poison'
                where id = %s
                """,
                (source["source_id"],),
            )
            return message
    finish_job(
        conn,
        job_id=claimed.job_id,
        source_id=str(source["source_id"]),
        observed_health=health,
        error_code=error_code,
        etag=etag,
        last_modified=last_modified,
        now=clock,
        rng=rng or Random(0),
    )
    logger.info(
        "job finished",
        extra={
            "job_id": claimed.job_id,
            "source_id": source["source_id"],
            "outcome": outcome,
            "error_code": error_code,
            "http_status": http_status,
            "strategy": "http",
        },
    )
    return message


def drain_once(
    conn: Any,
    *,
    worker_id: str | None = None,
    fetch: Any = None,
    now: datetime | None = None,
    rng: Random | None = None,
) -> list[str]:
    clock = now or datetime.now(UTC)
    owner = worker_id or f"cli:{os.getpid()}"
    schedule_due_sources(conn, clock)
    conn.commit()
    results: list[str] = []
    while True:
        claimed = claim_fetch_job(conn, owner, clock)
        if claimed is None:
            conn.commit()
            break
        conn.commit()
        results.append(
            run_claimed_job(conn, claimed, fetch=fetch, now=clock, rng=rng or Random(0))
        )
        conn.commit()
    return results


def fetch_stats(conn: Any, now: datetime | None = None) -> dict[str, int]:
    clock = now or datetime.now(UTC)

    def _count(sql: str, params: tuple[object, ...] = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        return int(row["n"] if row else 0)

    overdue = _count(
        """
        select count(*) as n from policy_sources
        where enabled and health_status <> 'quarantined' and due_at <= %s
        """,
        (clock,),
    )
    quarantined = _count(
        "select count(*) as n from policy_sources where health_status = 'quarantined'"
    )
    leased = _count(
        """
        select count(*) as n from policy_sources
        where lease_expires_at is not null and lease_expires_at > %s
        """,
        (clock,),
    )
    pending_jobs = _count(
        """
        select count(*) as n from fetch_jobs
        where status in ('pending', 'retryable_failed')
        """
    )
    return {
        "overdue_sources": overdue,
        "quarantined_sources": quarantined,
        "active_leases": leased,
        "pending_jobs": pending_jobs,
    }
