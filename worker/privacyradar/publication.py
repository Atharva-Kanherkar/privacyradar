"""Evidence validation, publication revisions, and corrections."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from privacyradar.extract import resolve_quote_span
from privacyradar.operator import OperatorError, validate_actor

logger = logging.getLogger(__name__)

PUBLISH_LOCK_KEY = 8462017
ALLOWED_TRANSITIONS = {
    "detected": {"analyzing", "review_pending", "rejected", "failed"},
    "analyzing": {"review_pending", "rejected", "failed"},
    "review_pending": {"published", "rejected", "failed"},
    "published": {"corrected"},
    "rejected": set(),
    "failed": set(),
    "corrected": set(),
}


class PublicationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _actor(actor: str) -> str:
    try:
        return validate_actor(actor)
    except OperatorError as exc:
        raise PublicationError("invalid_actor") from exc


@dataclass(frozen=True)
class PublishResult:
    revision_id: str
    revision_n: int
    n_claims: int


def _switch_enabled(conn: Any, key: str) -> bool:
    row = conn.execute("select enabled from product_switches where key = %s", (key,)).fetchone()
    return bool(row and row["enabled"])


def set_publication_enabled(conn: Any, enabled: bool) -> None:
    conn.execute(
        """
        update product_switches
        set enabled = %s, updated_at = now()
        where key = 'publication'
        """,
        (enabled,),
    )


def _audit(
    conn: Any,
    *,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    reason: str | None,
) -> None:
    conn.execute(
        """
        insert into review_actions (id, actor, action, target_type, target_id, reason)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (str(uuid4()), actor, action, target_type, target_id, reason),
    )


def validate_claim_for_publication(conn: Any, candidate_claim_id: str) -> str | None:
    row = conn.execute(
        """
        select distinct on (c.id)
          c.id,
          c.validation_state,
          c.category,
          c.attribute,
          c.polarity,
          e.quote,
          e.start_offset,
          e.end_offset,
          e.snapshot_id as span_snapshot_id,
          r.snapshot_id as run_snapshot_id,
          r.observation_id,
          s.markdown,
          o.snapshot_id as observation_snapshot_id
        from candidate_claims c
        join extraction_runs r on r.id = c.run_id
        join observations o on o.id = r.observation_id
        join snapshots s on s.id = r.snapshot_id
        left join evidence_spans e on e.claim_id = c.id
        where c.id = %s
        order by c.id, (e.validation_result = 'exact') desc, e.start_offset nulls last
        """,
        (candidate_claim_id,),
    ).fetchone()
    if row is None:
        return "missing_claim"
    if row["validation_state"] == "unsupported":
        return "unsupported"
    if row["validation_state"] == "invalid_category":
        return "invalid_category"
    if row["validation_state"] != "valid":
        return "unsupported"
    quote = row["quote"]
    markdown = str(row["markdown"] or "")
    if not quote:
        return "empty_quote"
    resolved = resolve_quote_span(str(quote), markdown)
    if resolved is None:
        return "quote_missing"
    _verbatim, start, end = resolved
    if row["span_snapshot_id"] is not None and str(row["span_snapshot_id"]) != str(
        row["run_snapshot_id"]
    ):
        return "snapshot_mismatch"
    if str(row["observation_snapshot_id"]) != str(row["run_snapshot_id"]):
        return "observation_mismatch"
    if row["start_offset"] is not None and int(row["start_offset"]) != start:
        return "offset_mismatch"
    if row["end_offset"] is not None and int(row["end_offset"]) != end:
        return "offset_mismatch"
    return None


def _current_revision_n(conn: Any, company_id: str) -> int:
    row = conn.execute(
        """
        select coalesce(max(revision_n), 0) as n
        from publication_revisions
        where company_id = %s
        """,
        (company_id,),
    ).fetchone()
    return int(row["n"] if row else 0)


def _company_id_for_run(conn: Any, run_id: str) -> dict[str, Any] | None:
    return cast(
        dict[str, Any] | None,
        conn.execute(
            """
            select
              r.id as run_id,
              r.observation_id,
              r.snapshot_id,
              r.taxonomy_version,
              s.is_valid,
              s.markdown,
              ps.company_id
            from extraction_runs r
            join snapshots s on s.id = r.snapshot_id
            join observations o on o.id = r.observation_id
            join policy_sources ps on ps.id = o.source_id
            where r.id = %s
            """,
            (run_id,),
        ).fetchone(),
    )


def publish_run(
    conn: Any,
    run_id: str,
    *,
    actor: str,
    change_event_id: str | None = None,
) -> PublishResult:
    actor = _actor(actor)
    if not _switch_enabled(conn, "publication"):
        raise PublicationError("publication_disabled")
    conn.execute("select pg_advisory_xact_lock(%s)", (PUBLISH_LOCK_KEY,))
    run = _company_id_for_run(conn, run_id)
    if run is None or not run["is_valid"] or not run["markdown"]:
        raise PublicationError("invalid_snapshot")
    claims = conn.execute(
        """
        select distinct on (c.id)
               c.id, c.claim_key, c.category, c.attribute, c.polarity,
               e.quote, e.start_offset, e.end_offset, e.snapshot_id
        from candidate_claims c
        left join evidence_spans e on e.claim_id = c.id
        where c.run_id = %s and c.validation_state = 'valid'
        order by c.id, (e.validation_result = 'exact') desc, e.start_offset nulls last
        """,
        (run_id,),
    ).fetchall()
    if not claims:
        raise PublicationError("no_valid_claims")
    for claim in claims:
        if not claim["quote"]:
            raise PublicationError("empty_quote")
        code = validate_claim_for_publication(conn, str(claim["id"]))
        if code:
            _audit(
                conn,
                actor=actor,
                action="reject",
                target_type="extraction_run",
                target_id=run_id,
                reason=code[:64],
            )
            raise PublicationError(code)
    revision_n = _current_revision_n(conn, str(run["company_id"])) + 1
    revision_id = str(uuid4())
    conn.execute(
        """
        insert into publication_revisions (
          id, company_id, observation_id, extraction_run_id, change_event_id,
          revision_n, state, actor, taxonomy_version
        )
        values (%s, %s, %s, %s, %s, %s, 'published', %s, %s)
        """,
        (
            revision_id,
            str(run["company_id"]),
            str(run["observation_id"]),
            run_id,
            change_event_id,
            revision_n,
            actor,
            str(run.get("taxonomy_version") or "1.0.0"),
        ),
    )
    markdown = str(run["markdown"])
    for claim in claims:
        resolved = resolve_quote_span(str(claim["quote"]), markdown)
        if resolved is None:
            raise PublicationError("quote_missing")
        verbatim, start, end = resolved
        snapshot_id = str(claim["snapshot_id"] or run["snapshot_id"])
        conn.execute(
            """
            insert into published_claims (
              id, revision_id, candidate_claim_id, claim_key, category, attribute,
              polarity, quote, snapshot_id, start_offset, end_offset
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                revision_id,
                str(claim["id"]),
                claim["claim_key"],
                claim["category"],
                claim["attribute"],
                claim["polarity"],
                verbatim,
                snapshot_id,
                start,
                end,
            ),
        )
    if change_event_id:
        _set_event_state(conn, change_event_id, "published", published=True)
    _audit(
        conn,
        actor=actor,
        action="publish",
        target_type="publication_revision",
        target_id=revision_id,
        reason="publish_run",
    )
    logger.info(
        "published revision",
        extra={
            "run_id": run_id,
            "revision_id": revision_id,
            "actor": actor,
            "n_claims": len(claims),
        },
    )
    if change_event_id:
        from privacyradar.notify import enqueue_fanout

        enqueue_fanout(conn, change_event_id, kind="publish")
    return PublishResult(revision_id=revision_id, revision_n=revision_n, n_claims=len(claims))


def _set_event_state(conn: Any, event_id: str, state: str, *, published: bool = False) -> None:
    row = conn.execute(
        "select publication_state from change_events where id = %s",
        (event_id,),
    ).fetchone()
    if row is None:
        raise PublicationError("missing_event")
    current = str(row["publication_state"])
    if current in {"rejected", "failed", "corrected"}:
        raise PublicationError("forbidden_transition")
    if state != current and state not in ALLOWED_TRANSITIONS.get(current, set()):
        raise PublicationError("forbidden_transition")
    if published:
        conn.execute(
            """
            update change_events
            set publication_state = %s, published_at = now()
            where id = %s
            """,
            (state, event_id),
        )
        return
    conn.execute(
        "update change_events set publication_state = %s where id = %s",
        (state, event_id),
    )


def reject_event(conn: Any, event_id: str, *, actor: str, reason: str) -> None:
    actor = _actor(actor)
    if "@" in reason or "://" in reason or len(reason) > 64:
        raise PublicationError("invalid_reason")
    _set_event_state(conn, event_id, "rejected")
    _audit(
        conn,
        actor=actor,
        action="reject",
        target_type="change_event",
        target_id=event_id,
        reason=reason,
    )


def publish_event(conn: Any, event_id: str, *, actor: str) -> None:
    actor = _actor(actor)
    if not _switch_enabled(conn, "publication"):
        raise PublicationError("publication_disabled")
    row = conn.execute(
        """
        select e.id, e.quotes, e.publication_state, s.markdown
        from change_events e
        join snapshots s on s.id = e.to_snapshot
        where e.id = %s
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        raise PublicationError("missing_event")
    markdown = str(row["markdown"] or "")
    quotes = row["quotes"] or []
    if isinstance(quotes, str):
        quotes = []
    if not quotes:
        raise PublicationError("quote_missing")
    for item in quotes:
        text = item.get("text") if isinstance(item, dict) else ""
        if not text or resolve_quote_span(str(text), markdown) is None:
            raise PublicationError("quote_missing")
    _set_event_state(conn, event_id, "published", published=True)
    _audit(
        conn,
        actor=actor,
        action="publish",
        target_type="change_event",
        target_id=event_id,
        reason="publish_event",
    )
    from privacyradar.notify import enqueue_fanout

    enqueue_fanout(conn, event_id, kind="publish")


def rollback_revision(conn: Any, revision_id: str, *, actor: str, reason: str) -> PublishResult:
    actor = _actor(actor)
    if not _switch_enabled(conn, "publication"):
        raise PublicationError("publication_disabled")
    if "@" in reason or "://" in reason or len(reason) > 64:
        raise PublicationError("invalid_reason")
    conn.execute("select pg_advisory_xact_lock(%s)", (PUBLISH_LOCK_KEY,))
    target = conn.execute(
        """
        select
          id, company_id, observation_id, extraction_run_id, change_event_id,
          state, taxonomy_version
        from publication_revisions
        where id = %s
        """,
        (revision_id,),
    ).fetchone()
    if target is None or target["state"] != "published":
        raise PublicationError("missing_revision")
    marker_n = _current_revision_n(conn, str(target["company_id"])) + 1
    marker_id = str(uuid4())
    conn.execute(
        """
        insert into publication_revisions (
          id, company_id, observation_id, extraction_run_id, change_event_id,
          rolls_back_id, revision_n, state, actor, taxonomy_version
        )
        values (%s, %s, %s, %s, %s, %s, %s, 'rolled_back', %s, %s)
        """,
        (
            marker_id,
            str(target["company_id"]),
            str(target["observation_id"]),
            str(target["extraction_run_id"]),
            target["change_event_id"],
            revision_id,
            marker_n,
            actor,
            str(target.get("taxonomy_version") or "1.0.0"),
        ),
    )
    _audit(
        conn,
        actor=actor,
        action="rollback",
        target_type="publication_revision",
        target_id=revision_id,
        reason=reason,
    )
    prior = conn.execute(
        """
        select id, extraction_run_id, change_event_id
        from publication_revisions pr
        where company_id = %s
          and state = 'published'
          and id <> %s
          and not exists (
            select 1 from publication_revisions rb where rb.rolls_back_id = pr.id
          )
        order by revision_n desc
        limit 1
        """,
        (str(target["company_id"]), revision_id),
    ).fetchone()
    abandoned = str(target["change_event_id"]) if target["change_event_id"] else None
    if prior:
        restore_run = str(prior["extraction_run_id"])
        restore_event = str(prior["change_event_id"]) if prior["change_event_id"] else None
        result = publish_run(
            conn,
            restore_run,
            actor=actor,
            change_event_id=restore_event,
        )
        if abandoned and abandoned != restore_event:
            conn.execute(
                """
                update change_events
                set publication_state = 'corrected'
                where id = %s and publication_state = 'published'
                """,
                (abandoned,),
            )
            from privacyradar.notify import enqueue_fanout

            enqueue_fanout(conn, abandoned, kind="correction")
        return result
    if abandoned:
        conn.execute(
            """
            update change_events
            set publication_state = 'corrected'
            where id = %s and publication_state = 'published'
            """,
            (abandoned,),
        )
        from privacyradar.notify import enqueue_fanout

        enqueue_fanout(conn, abandoned, kind="correction")
    return PublishResult(revision_id=marker_id, revision_n=marker_n, n_claims=0)


def submit_correction(
    conn: Any,
    *,
    company_id: str,
    revision_id: str,
    note: str,
    actor: str,
) -> str:
    actor = _actor(actor)
    if not note.strip():
        raise PublicationError("note_required")
    correction_id = str(uuid4())
    conn.execute(
        """
        insert into corrections (
          id, company_id, target_revision_id, reporter_kind, state, public_note, actor
        )
        values (%s, %s, %s, 'operator', 'submitted', %s, %s)
        """,
        (correction_id, company_id, revision_id, note.strip()[:500], actor),
    )
    _audit(
        conn,
        actor=actor,
        action="acknowledge",
        target_type="correction",
        target_id=correction_id,
        reason="submitted",
    )
    return correction_id


def resolve_correction(
    conn: Any,
    correction_id: str,
    *,
    actor: str,
    decision: str,
    note: str,
) -> str | None:
    actor = _actor(actor)
    row = conn.execute("select * from corrections where id = %s", (correction_id,)).fetchone()
    if row is None:
        raise PublicationError("missing_correction")
    if decision == "declined":
        conn.execute(
            """
            update corrections
            set state = 'declined', actor = %s, public_note = %s, resolved_at = now()
            where id = %s
            """,
            (actor, note.strip()[:500], correction_id),
        )
        _audit(
            conn,
            actor=actor,
            action="decline",
            target_type="correction",
            target_id=correction_id,
            reason="declined",
        )
        return None
    if decision != "corrected":
        raise PublicationError("invalid_decision")
    if not note.strip():
        raise PublicationError("note_required")
    published = publish_run(
        conn,
        str(
            conn.execute(
                "select extraction_run_id from publication_revisions where id = %s",
                (str(row["target_revision_id"]),),
            ).fetchone()["extraction_run_id"]
        ),
        actor=actor,
    )
    conn.execute(
        """
        update corrections
        set state = 'corrected',
            replacement_revision_id = %s,
            actor = %s,
            public_note = %s,
            resolved_at = now()
        where id = %s
        """,
        (published.revision_id, actor, note.strip()[:500], correction_id),
    )
    event = conn.execute(
        "select change_event_id from publication_revisions where id = %s",
        (str(row["target_revision_id"]),),
    ).fetchone()
    if event and event["change_event_id"]:
        conn.execute(
            """
            update change_events
            set publication_state = 'corrected'
            where id = %s and publication_state = 'published'
            """,
            (str(event["change_event_id"]),),
        )
        from privacyradar.notify import enqueue_fanout

        enqueue_fanout(conn, str(event["change_event_id"]), kind="correction")
    _audit(
        conn,
        actor=actor,
        action="correct",
        target_type="correction",
        target_id=correction_id,
        reason="corrected",
    )
    return published.revision_id


def publish_stats(conn: Any) -> dict[str, int]:
    pending = conn.execute(
        "select count(*) as n from change_events where publication_state = 'review_pending'"
    ).fetchone()
    revisions = conn.execute(
        "select count(*) as n from publication_revisions where state = 'published'"
    ).fetchone()
    rollbacks = conn.execute(
        "select count(*) as n from publication_revisions where state = 'rolled_back'"
    ).fetchone()
    failures = conn.execute(
        "select count(*) as n from review_actions where action = 'reject'"
    ).fetchone()
    open_corr = conn.execute(
        """
        select count(*) as n from corrections
        where state in ('submitted', 'acknowledged', 'reviewing')
        """
    ).fetchone()
    oldest = conn.execute(
        """
        select extract(epoch from (now() - min(created_at)))::int as age
        from change_events
        where publication_state = 'review_pending'
        """
    ).fetchone()
    return {
        "review_pending": int(pending["n"] if pending else 0),
        "published_revisions": int(revisions["n"] if revisions else 0),
        "rollbacks": int(rollbacks["n"] if rollbacks else 0),
        "citation_failures": int(failures["n"] if failures else 0),
        "queue_age_seconds": int(oldest["age"] if oldest and oldest["age"] is not None else 0),
        "corrections_open": int(open_corr["n"] if open_corr else 0),
    }


def event_state_for_materiality(materiality: str) -> str:
    if materiality == "cosmetic":
        return "rejected"
    if materiality in {"material", "unknown"}:
        return "review_pending"
    return "detected"
