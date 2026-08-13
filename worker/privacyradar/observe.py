"""Append-only observation recording. Hash comparison is deterministic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg.errors import UniqueViolation
from psycopg.types.json import Json

from privacyradar.classify import Classification, classify_fetch
from privacyradar.crawl import FetchResult
from privacyradar.hashing import NORMALIZER_VERSION, changed_sections

logger = logging.getLogger(__name__)

HEALTH_QUARANTINE_AFTER = 5


@dataclass(frozen=True)
class ObserveMetrics:
    fetch_attempts: int = 0
    new_versions: int = 0
    deduped: int = 0
    normalization_failures: int = 0
    failed_attempts: int = 0


@dataclass(frozen=True)
class ObserveResult:
    outcome: str
    message: str
    error_code: str | None
    attempt_id: str
    snapshot_id: str | None
    observation_id: str | None
    document_change_id: str | None
    current_snapshot_id: str | None
    health_status: str
    metrics: ObserveMetrics


def _health_after_failure(consecutive: int) -> str:
    if consecutive >= HEALTH_QUARANTINE_AFTER:
        return "quarantined"
    if consecutive >= 1:
        return "degraded"
    return "pending"


def observe_source(
    conn: Any,
    source: dict[str, Any],
    fetched: FetchResult,
    *,
    clock: datetime | None = None,
) -> ObserveResult:
    """Record one fetch. Must run inside a caller-owned transaction."""
    now = clock or datetime.now(UTC)
    source_id = str(source["source_id"])
    company_id = str(source["company_id"])
    slug = str(source["slug"])
    region = str(source.get("region") or "global")
    request_url = str(source["url"])
    classification = classify_fetch(fetched)
    attempt_id = str(uuid4())

    current = conn.execute(
        """
        select current_snapshot_id, current_observation_id, consecutive_failures,
               health_status
        from policy_sources
        where id = %s
        for update
        """,
        (source_id,),
    ).fetchone()
    if current is None:
        raise RuntimeError(f"unknown source {source_id}")

    previous_snapshot_id = (
        str(current["current_snapshot_id"]) if current["current_snapshot_id"] else None
    )
    previous_observation_id = (
        str(current["current_observation_id"]) if current["current_observation_id"] else None
    )
    consecutive = int(current["consecutive_failures"] or 0)

    if not classification.valid:
        consecutive += 1
        health = _health_after_failure(consecutive)
        conn.execute(
            """
            insert into source_attempts (
              id, source_id, started_at, finished_at, strategy, status,
              http_status, content_type, request_url, resolved_url, error_code,
              byte_count, normalizer_version
            )
            values (%s, %s, %s, %s, 'http', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                attempt_id,
                source_id,
                now,
                now,
                classification.status,
                fetched.status,
                fetched.content_type,
                request_url,
                fetched.url,
                classification.error_code,
                len(fetched.body or fetched.html.encode("utf-8")),
                NORMALIZER_VERSION,
            ),
        )
        conn.execute(
            """
            update policy_sources
            set health_status = %s,
                last_attempt_at = %s,
                last_failure_code = %s,
                consecutive_failures = %s
            where id = %s
            """,
            (health, now, classification.error_code, consecutive, source_id),
        )
        normalize_fail = 1 if classification.error_code == "normalize_failed" else 0
        logger.info(
            "observe failed",
            extra={
                "source_id": source_id,
                "attempt_id": attempt_id,
                "outcome": "failed",
                "error_code": classification.error_code,
                "normalizer_version": NORMALIZER_VERSION,
            },
        )
        return ObserveResult(
            outcome="failed",
            message=f"{slug}: fetch failed ({classification.error_code})",
            error_code=classification.error_code,
            attempt_id=attempt_id,
            snapshot_id=None,
            observation_id=None,
            document_change_id=None,
            current_snapshot_id=previous_snapshot_id,
            health_status=health,
            metrics=ObserveMetrics(
                fetch_attempts=1,
                failed_attempts=1,
                normalization_failures=normalize_fail,
            ),
        )

    assert classification.normalized is not None
    normalized = classification.normalized
    digest = normalized.normalized_sha256
    snapshot_id, _created = _get_or_insert_snapshot(
        conn,
        source_id=source_id,
        fetched=fetched,
        classification=classification,
        region=region,
        now=now,
    )

    if previous_snapshot_id == snapshot_id:
        conn.execute(
            """
            insert into source_attempts (
              id, source_id, started_at, finished_at, strategy, status,
              http_status, content_type, request_url, resolved_url,
              snapshot_id, byte_count, normalizer_version
            )
            values (%s, %s, %s, %s, 'http', 'succeeded', %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                attempt_id,
                source_id,
                now,
                now,
                fetched.status,
                fetched.content_type,
                request_url,
                fetched.url,
                snapshot_id,
                normalized.byte_count,
                NORMALIZER_VERSION,
            ),
        )
        conn.execute(
            """
            update policy_sources
            set health_status = 'healthy',
                last_attempt_at = %s,
                last_success_at = %s,
                last_failure_code = null,
                consecutive_failures = 0
            where id = %s
            """,
            (now, now, source_id),
        )
        logger.info(
            "observe deduped",
            extra={
                "source_id": source_id,
                "attempt_id": attempt_id,
                "snapshot_id": snapshot_id,
                "outcome": "deduped",
                "normalizer_version": NORMALIZER_VERSION,
            },
        )
        return ObserveResult(
            outcome="deduped",
            message=f"{slug}: unchanged ({digest[:10]})",
            error_code=None,
            attempt_id=attempt_id,
            snapshot_id=snapshot_id,
            observation_id=previous_observation_id,
            document_change_id=None,
            current_snapshot_id=snapshot_id,
            health_status="healthy",
            metrics=ObserveMetrics(fetch_attempts=1, deduped=1),
        )

    observation_id = str(uuid4())
    conn.execute(
        """
        insert into source_attempts (
          id, source_id, started_at, finished_at, strategy, status,
          http_status, content_type, request_url, resolved_url,
          snapshot_id, byte_count, normalizer_version
        )
        values (%s, %s, %s, %s, 'http', 'succeeded', %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            attempt_id,
            source_id,
            now,
            now,
            fetched.status,
            fetched.content_type,
            request_url,
            fetched.url,
            snapshot_id,
            normalized.byte_count,
            NORMALIZER_VERSION,
        ),
    )
    conn.execute(
        """
        insert into observations (
          id, source_id, snapshot_id, attempt_id, observed_at, region,
          previous_snapshot_id
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            observation_id,
            source_id,
            snapshot_id,
            attempt_id,
            now,
            region,
            previous_snapshot_id,
        ),
    )
    conn.execute(
        """
        update source_attempts
        set observation_id = %s
        where id = %s
        """,
        (observation_id, attempt_id),
    )

    change_id: str | None = None
    if previous_snapshot_id is not None:
        change_id = str(uuid4())
        old_sections = conn.execute(
            "select section_hashes from snapshots where id = %s",
            (previous_snapshot_id,),
        ).fetchone()
        old_map = dict((old_sections or {}).get("section_hashes") or {})
        new_map = dict(normalized.section_hashes)
        changed = changed_sections(old_map, new_map)
        added = sorted(name for name in new_map if name not in old_map)
        removed = sorted(name for name in old_map if name not in new_map)
        modified = sorted(
            name for name in changed if name in old_map and name in new_map
        )
        conn.execute(
            """
            insert into document_changes (
              id, company_id, source_id, from_snapshot_id, to_snapshot_id,
              from_observation_id, to_observation_id,
              added_sections, removed_sections, modified_sections,
              normalizer_version
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                change_id,
                company_id,
                source_id,
                previous_snapshot_id,
                snapshot_id,
                previous_observation_id,
                observation_id,
                added,
                removed,
                modified,
                NORMALIZER_VERSION,
            ),
        )

    conn.execute(
        """
        update policy_sources
        set current_snapshot_id = %s,
            current_observation_id = %s,
            health_status = 'healthy',
            last_attempt_at = %s,
            last_success_at = %s,
            last_failure_code = null,
            consecutive_failures = 0
        where id = %s
        """,
        (snapshot_id, observation_id, now, now, source_id),
    )
    logger.info(
        "observe new_version",
        extra={
            "source_id": source_id,
            "attempt_id": attempt_id,
            "snapshot_id": snapshot_id,
            "outcome": "new_version",
            "normalizer_version": NORMALIZER_VERSION,
        },
    )
    if previous_snapshot_id is None:
        message = f"{slug}: first snapshot stored"
    else:
        message = f"{slug}: hash changed ({digest[:10]})"
    return ObserveResult(
        outcome="new_version",
        message=message,
        error_code=None,
        attempt_id=attempt_id,
        snapshot_id=snapshot_id,
        observation_id=observation_id,
        document_change_id=change_id,
        current_snapshot_id=snapshot_id,
        health_status="healthy",
        metrics=ObserveMetrics(fetch_attempts=1, new_versions=1),
    )


def _get_or_insert_snapshot(
    conn: Any,
    *,
    source_id: str,
    fetched: FetchResult,
    classification: Classification,
    region: str,
    now: datetime,
) -> tuple[str, bool]:
    assert classification.normalized is not None
    normalized = classification.normalized
    existing = conn.execute(
        """
        select id from snapshots
        where source_id = %s
          and doc_hash = %s
          and normalizer_version = %s
        """,
        (source_id, normalized.normalized_sha256, NORMALIZER_VERSION),
    ).fetchone()
    if existing is not None:
        return str(existing["id"]), False

    snapshot_id = str(uuid4())
    try:
        with conn.transaction():
            conn.execute(
                """
                insert into snapshots (
                  id, source_id, fetched_at, http_status, content_type, raw_html,
                  markdown, doc_hash, section_hashes, fetch_error, final_url,
                  region, strategy, byte_count, raw_sha256, normalized_sha256,
                  normalizer_version, is_valid
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, null, %s, %s, 'http',
                  %s, %s, %s, %s, true
                )
                """,
                (
                    snapshot_id,
                    source_id,
                    now,
                    fetched.status,
                    fetched.content_type,
                    fetched.html,
                    normalized.markdown,
                    normalized.normalized_sha256,
                    Json(normalized.section_hashes),
                    fetched.url,
                    region,
                    normalized.byte_count,
                    normalized.raw_sha256,
                    normalized.normalized_sha256,
                    NORMALIZER_VERSION,
                ),
            )
        return snapshot_id, True
    except UniqueViolation:
        raced = conn.execute(
            """
            select id from snapshots
            where source_id = %s
              and doc_hash = %s
              and normalizer_version = %s
            """,
            (source_id, normalized.normalized_sha256, NORMALIZER_VERSION),
        ).fetchone()
        if raced is not None:
            return str(raced["id"]), False
        raise
