"""Idempotent backfill of observations from 0001-era snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReconcileReport:
    sources: int
    valid_snapshots: int
    invalid_snapshots: int
    observations_created: int
    attempts_created: int
    current_pointers_set: int


def reconcile_observations(conn: Any) -> ReconcileReport:
    sources = conn.execute("select count(*) as n from policy_sources").fetchone()["n"]
    valid_before = conn.execute(
        "select count(*) as n from snapshots where is_valid"
    ).fetchone()["n"]
    invalid_before = conn.execute(
        "select count(*) as n from snapshots where not is_valid"
    ).fetchone()["n"]
    observations_before = conn.execute(
        "select count(*) as n from observations"
    ).fetchone()["n"]
    attempts_before = conn.execute(
        "select count(*) as n from source_attempts"
    ).fetchone()["n"]
    pointers_before = conn.execute(
        "select count(*) as n from policy_sources where current_snapshot_id is not null"
    ).fetchone()["n"]

    conn.execute(
        """
        insert into source_attempts (
          source_id, started_at, finished_at, strategy, status,
          http_status, content_type, request_url, resolved_url,
          snapshot_id, byte_count, normalizer_version
        )
        select
          s.source_id, s.fetched_at, s.fetched_at, s.strategy, 'succeeded',
          s.http_status, s.content_type, ps.url, coalesce(s.final_url, ps.url),
          s.id, s.byte_count, s.normalizer_version
        from snapshots s
        join policy_sources ps on ps.id = s.source_id
        where s.is_valid
          and not exists (
            select 1 from source_attempts a where a.snapshot_id = s.id
          )
        """
    )
    conn.execute(
        """
        insert into source_attempts (
          source_id, started_at, finished_at, strategy, status,
          http_status, content_type, request_url, resolved_url,
          error_code, byte_count, normalizer_version
        )
        select
          s.source_id, s.fetched_at, s.fetched_at, s.strategy, 'failed',
          s.http_status, s.content_type, ps.url, coalesce(s.final_url, ps.url),
          case
            when s.fetch_error in (
              'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx',
              'empty', 'short', 'wrong_type', 'normalize_failed', 'network', 'blocked'
            ) then s.fetch_error
            when s.doc_hash = 'empty' or coalesce(s.markdown, '') = '' then 'empty'
            else 'network'
          end,
          s.byte_count, s.normalizer_version
        from snapshots s
        join policy_sources ps on ps.id = s.source_id
        where not s.is_valid
          and not exists (
            select 1 from source_attempts a
            where a.source_id = s.source_id
              and a.started_at = s.fetched_at
              and a.status = 'failed'
          )
        """
    )
    conn.execute(
        """
        insert into observations (
          source_id, snapshot_id, attempt_id, observed_at, region, previous_snapshot_id
        )
        select distinct on (s.id)
          s.source_id, s.id, a.id, s.fetched_at, s.region, null
        from snapshots s
        join source_attempts a
          on a.snapshot_id = s.id and a.status = 'succeeded'
        where s.is_valid
          and not exists (
            select 1 from observations o where o.snapshot_id = s.id
          )
        order by s.id, a.started_at
        """
    )
    conn.execute(
        """
        update source_attempts a
        set observation_id = o.id
        from observations o
        where o.attempt_id = a.id
          and a.observation_id is null
        """
    )
    conn.execute(
        """
        update policy_sources ps
        set
          current_snapshot_id = x.snapshot_id,
          current_observation_id = x.observation_id,
          health_status = 'healthy',
          last_success_at = x.observed_at,
          last_attempt_at = coalesce(ps.last_attempt_at, x.observed_at)
        from (
          select distinct on (o.source_id)
            o.source_id, o.snapshot_id, o.id as observation_id, o.observed_at
          from observations o
          order by o.source_id, o.observed_at desc
        ) x
        where ps.id = x.source_id
          and ps.current_snapshot_id is null
        """
    )

    observations_after = conn.execute(
        "select count(*) as n from observations"
    ).fetchone()["n"]
    attempts_after = conn.execute(
        "select count(*) as n from source_attempts"
    ).fetchone()["n"]
    pointers_after = conn.execute(
        "select count(*) as n from policy_sources where current_snapshot_id is not null"
    ).fetchone()["n"]
    return ReconcileReport(
        sources=int(sources),
        valid_snapshots=int(valid_before),
        invalid_snapshots=int(invalid_before),
        observations_created=int(observations_after - observations_before),
        attempts_created=int(attempts_after - attempts_before),
        current_pointers_set=int(pointers_after - pointers_before),
    )


def format_report(report: ReconcileReport) -> str:
    return (
        "reconcile "
        f"sources={report.sources} "
        f"valid_snapshots={report.valid_snapshots} "
        f"invalid_snapshots={report.invalid_snapshots} "
        f"observations_created={report.observations_created} "
        f"attempts_created={report.attempts_created} "
        f"current_pointers_set={report.current_pointers_set}"
    )
