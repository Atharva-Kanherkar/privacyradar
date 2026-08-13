"""Operator replay/disable/enable with an audit row. Actor is never an email."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from psycopg.types.json import Json

ACTOR_RE = re.compile(r"^[a-z0-9][a-z0-9:_-]{1,62}$")


class OperatorError(ValueError):
    pass


def validate_actor(actor: str) -> str:
    if "@" in actor or "://" in actor or ACTOR_RE.fullmatch(actor) is None:
        raise OperatorError("invalid actor")
    return actor


def _require_source(conn: Any, source_id: str) -> dict[str, Any]:
    source = conn.execute(
        "select * from policy_sources where id = %s for update",
        (source_id,),
    ).fetchone()
    if source is None:
        raise OperatorError("unknown source")
    return cast(dict[str, Any], source)


def _audit(
    conn: Any,
    *,
    action_id: str,
    source_id: str,
    action: str,
    actor: str,
    reason: str,
    metadata: dict[str, str],
) -> None:
    conn.execute(
        """
        insert into source_operator_actions (
          id, source_id, action, actor, reason, metadata
        )
        values (%s, %s, %s, %s, %s, %s)
        """,
        (action_id, source_id, action, actor, reason, Json(metadata)),
    )


def source_retry(conn: Any, source_id: str, *, actor: str, now: datetime | None = None) -> str:
    actor = validate_actor(actor)
    clock = now or datetime.now(UTC)
    source = _require_source(conn, source_id)
    health = "degraded" if source["current_snapshot_id"] else "pending"
    action_id = str(uuid4())
    job_key = f"fetch:{source_id}:retry:{action_id}"
    _audit(
        conn,
        action_id=action_id,
        source_id=source_id,
        action="retry",
        actor=actor,
        reason="operator_retry",
        metadata={"job_key": job_key},
    )
    conn.execute(
        """
        update policy_sources
        set enabled = true,
            health_status = %s,
            consecutive_failures = 0,
            retry_count = 0,
            due_at = %s,
            quarantine_reason = null,
            quarantined_at = null,
            lease_owner = null,
            lease_token = null,
            lease_expires_at = null
        where id = %s
        """,
        (health, clock, source_id),
    )
    conn.execute(
        """
        insert into fetch_jobs (idempotency_key, source_id, status, run_after)
        values (%s, %s, 'pending', %s)
        """,
        (job_key, source_id, clock),
    )
    return action_id


def source_disable(conn: Any, source_id: str, *, actor: str) -> str:
    actor = validate_actor(actor)
    _require_source(conn, source_id)
    action_id = str(uuid4())
    _audit(
        conn,
        action_id=action_id,
        source_id=source_id,
        action="disable",
        actor=actor,
        reason="operator_disable",
        metadata={},
    )
    conn.execute(
        """
        update policy_sources
        set enabled = false,
            lease_owner = null,
            lease_token = null,
            lease_expires_at = null
        where id = %s
        """,
        (source_id,),
    )
    conn.execute(
        """
        update fetch_jobs
        set status = 'cancelled',
            finished_at = now(),
            lease_owner = null,
            lease_token = null,
            lease_expires_at = null
        where source_id = %s
          and status in ('pending', 'retryable_failed', 'leased')
        """,
        (source_id,),
    )
    return action_id


def source_enable(conn: Any, source_id: str, *, actor: str, now: datetime | None = None) -> str:
    actor = validate_actor(actor)
    clock = now or datetime.now(UTC)
    _require_source(conn, source_id)
    action_id = str(uuid4())
    _audit(
        conn,
        action_id=action_id,
        source_id=source_id,
        action="enable",
        actor=actor,
        reason="operator_enable",
        metadata={},
    )
    conn.execute(
        """
        update policy_sources
        set enabled = true,
            due_at = %s
        where id = %s
        """,
        (clock, source_id),
    )
    return action_id
