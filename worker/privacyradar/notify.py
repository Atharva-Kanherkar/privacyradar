"""Publication fan-out and leased outbox delivery. Never calls the provider in publish."""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from psycopg.errors import UniqueViolation

from privacyradar.notify_mail import (
    NotifyError,
    email_hash,
    fixture_delivery_enabled,
    get_provider,
    render_alert,
    sign_unsub_token,
)

logger = logging.getLogger(__name__)

FANOUT_PAGE = 100
LEASE_SECONDS = 60
MAX_ATTEMPTS = 8
WORKER_ID = f"notify-{os.getpid()}-{uuid4().hex[:8]}"


def _switch_enabled(conn: Any, key: str) -> bool:
    row = conn.execute("select enabled from product_switches where key = %s", (key,)).fetchone()
    return bool(row and row["enabled"])


def enqueue_fanout(conn: Any, event_id: str, *, kind: str = "publish") -> str | None:
    if kind not in {"publish", "correction"}:
        raise NotifyError("invalid_kind")
    if not _switch_enabled(conn, "notifications"):
        return None
    row = conn.execute(
        """
        select publication_state, materiality
        from change_events
        where id = %s
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        return None
    if row["materiality"] != "material":
        return None
    if kind == "publish" and row["publication_state"] != "published":
        return None
    if kind == "correction" and row["publication_state"] not in {"published", "corrected"}:
        return None
    inserted = conn.execute(
        """
        insert into notification_fanout_jobs (event_id, kind, state)
        values (%s, %s, 'pending')
        on conflict (event_id, kind) do nothing
        returning id
        """,
        (event_id, kind),
    ).fetchone()
    return str(inserted["id"]) if inserted else None


def next_monday_noon_utc(now: datetime | None = None) -> datetime:
    stamp = (now or datetime.now(UTC)).astimezone(UTC)
    days = (7 - stamp.weekday()) % 7
    candidate = stamp.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days)
    if candidate <= stamp:
        candidate += timedelta(days=7)
    return candidate


def _preference(conn: Any, user_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        select frequency, muted_company_ids
        from notification_preferences
        where user_id = %s and channel = 'email'
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return {"frequency": "immediate", "muted_company_ids": []}
    muted = row["muted_company_ids"] or []
    return {"frequency": str(row["frequency"]), "muted_company_ids": list(muted)}


def _email_for_user(conn: Any, user_id: str) -> str | None:
    row = conn.execute("select email from auth_users where id = %s", (user_id,)).fetchone()
    if row is None or not row["email"]:
        return None
    return str(row["email"])


def _suppressed(conn: Any, email: str) -> bool:
    row = conn.execute(
        "select 1 from notification_suppressions where email_hash = %s",
        (email_hash(email),),
    ).fetchone()
    return row is not None


def _eligible_for_publish(
    conn: Any,
    *,
    user_id: str,
    company_id: str,
    email: str | None,
) -> tuple[bool, str, datetime | None]:
    if not email or _suppressed(conn, email):
        return False, "suppressed", None
    watch = conn.execute(
        """
        select status from watches
        where user_id = %s and company_id = %s
        """,
        (user_id, company_id),
    ).fetchone()
    if watch is None or watch["status"] != "active":
        return False, "cancelled", None
    pref = _preference(conn, user_id)
    if pref["frequency"] == "unsubscribed":
        return False, "cancelled", None
    muted = {str(item) for item in pref["muted_company_ids"]}
    if company_id in muted:
        return False, "cancelled", None
    when: datetime | None = None
    if pref["frequency"] == "digest_weekly":
        when = next_monday_noon_utc()
    return True, "pending", when


def run_fanout(conn: Any, *, limit: int = 20) -> int:
    processed = 0
    for _ in range(limit):
        job = conn.execute(
            """
            with picked as (
              select id from notification_fanout_jobs
              where state in ('pending', 'running')
                and (state = 'pending' or lease_expires_at is null or lease_expires_at < now())
              order by created_at
              for update skip locked
              limit 1
            )
            update notification_fanout_jobs j
            set state = 'running',
                claimed_at = now(),
                claimed_by = %s,
                lease_expires_at = now() + (%s * interval '1 second')
            from picked
            where j.id = picked.id
            returning j.id, j.event_id, j.kind, j.cursor_user_id, j.written_count
            """,
            (WORKER_ID, LEASE_SECONDS),
        ).fetchone()
        if job is None:
            break
        _fanout_one(conn, job)
        processed += 1
    return processed


def _fanout_one(conn: Any, job: dict[str, Any]) -> None:
    event = conn.execute(
        """
        select e.id, e.company_id, e.publication_state, e.materiality
        from change_events e
        where e.id = %s
        """,
        (str(job["event_id"]),),
    ).fetchone()
    if event is None or event["materiality"] != "material":
        conn.execute(
            "update notification_fanout_jobs set state = 'done' where id = %s",
            (str(job["id"]),),
        )
        return
    cursor = str(job["cursor_user_id"] or "")
    written = int(job["written_count"] or 0)
    kind = str(job["kind"])
    revision = 2 if kind == "correction" else 1
    while True:
        if kind == "correction":
            rows = conn.execute(
                """
                select o.user_id
                from notification_outbox o
                where o.event_id = %s
                  and o.revision = 1
                  and o.state = 'sent'
                  and o.user_id > %s
                order by o.user_id
                limit %s
                """,
                (str(job["event_id"]), cursor, FANOUT_PAGE),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select w.user_id
                from watches w
                where w.company_id = %s
                  and w.status = 'active'
                  and w.user_id > %s
                order by w.user_id
                limit %s
                """,
                (str(event["company_id"]), cursor, FANOUT_PAGE),
            ).fetchall()
        if not rows:
            break
        for row in rows:
            user_id = str(row["user_id"])
            cursor = user_id
            email = _email_for_user(conn, user_id)
            if kind == "publish":
                ok, _state, when = _eligible_for_publish(
                    conn,
                    user_id=user_id,
                    company_id=str(event["company_id"]),
                    email=email,
                )
                if not ok:
                    continue
            else:
                if not email or _suppressed(conn, email):
                    continue
                pref = _preference(conn, user_id)
                if pref["frequency"] == "unsubscribed":
                    continue
                when = None
            inserted = conn.execute(
                """
                insert into notification_outbox (
                  user_id, event_id, channel, revision, kind, state, next_attempt_at
                )
                values (%s, %s, 'email', %s, %s, 'pending', coalesce(%s, now()))
                on conflict (user_id, event_id, channel, revision) do nothing
                returning id
                """,
                (user_id, str(job["event_id"]), revision, kind, when),
            ).fetchone()
            if inserted:
                written += 1
        conn.execute(
            """
            update notification_fanout_jobs
            set cursor_user_id = %s,
                written_count = %s,
                lease_expires_at = now() + (%s * interval '1 second')
            where id = %s
            """,
            (cursor, written, LEASE_SECONDS, str(job["id"])),
        )
        if len(rows) < FANOUT_PAGE:
            break
    conn.execute(
        """
        update notification_fanout_jobs
        set state = 'done', written_count = %s, expected_count = %s
        where id = %s
        """,
        (written, written, str(job["id"])),
    )


def run_deliver(conn: Any, *, limit: int = 50) -> int:
    if not _switch_enabled(conn, "notifications"):
        return 0
    sent = 0
    provider = get_provider()
    for _ in range(limit):
        row = conn.execute(
            """
            with picked as (
              select id from notification_outbox
              where state in ('pending', 'failed', 'claimed')
                and next_attempt_at <= now()
                and (state <> 'claimed' or lease_expires_at is null or lease_expires_at < now())
              order by next_attempt_at
              for update skip locked
              limit 1
            )
            update notification_outbox o
            set state = 'claimed',
                claimed_at = now(),
                claimed_by = %s,
                lease_expires_at = now() + (%s * interval '1 second'),
                attempt_count = attempt_count + 1
            from picked
            where o.id = picked.id
            returning o.*
            """,
            (WORKER_ID, LEASE_SECONDS),
        ).fetchone()
        if row is None:
            break
        if _deliver_one(conn, row, provider):
            sent += 1
    return sent


def _deliver_one(conn: Any, row: dict[str, Any], provider: Any) -> bool:
    event = conn.execute(
        """
        select e.id, e.headline, e.summary, e.company_id, e.materiality,
               e.publication_state, e.data_types_added, c.name as company_name
        from change_events e
        join companies c on c.id = e.company_id
        where e.id = %s
        """,
        (str(row["event_id"]),),
    ).fetchone()
    if event is None:
        _finish(conn, str(row["id"]), "cancelled")
        return False
    email = _email_for_user(conn, str(row["user_id"]))
    ok, state, _when = _eligible_for_publish(
        conn,
        user_id=str(row["user_id"]),
        company_id=str(event["company_id"]),
        email=email,
    )
    if not ok:
        _finish(conn, str(row["id"]), state)
        return False
    if str(row["kind"]) == "publish" and (
        event["publication_state"] != "published" or event["materiality"] != "material"
    ):
        _finish(conn, str(row["id"]), "cancelled")
        return False
    already = conn.execute(
        """
        select 1 from notification_deliveries
        where outbox_id = %s and state = 'sent'
        """,
        (str(row["id"]),),
    ).fetchone()
    if already:
        _finish(conn, str(row["id"]), "sent")
        return True
    assert email is not None
    token = sign_unsub_token(user_id=str(row["user_id"]))
    rendered = render_alert(
        company_name=str(event["company_name"]),
        headline=str(event["headline"]),
        summary=str(event["summary"]),
        event_id=str(event["id"]),
        kind=str(row["kind"]),
        unsubscribe_token=token,
        data_types_added=list(event["data_types_added"] or []),
    )
    try:
        result = provider.send(
            conn,
            to_email=email,
            rendered=rendered,
            idempotency_key=str(row["id"]),
        )
    except NotifyError:
        _retry_or_fail(conn, row)
        return False
    with suppress(UniqueViolation):
        conn.execute(
            """
            insert into notification_deliveries (
              outbox_id, provider, provider_message_id, state
            )
            values (%s, %s, %s, 'sent')
            """,
            (str(row["id"]), result.provider, result.provider_message_id),
        )
    _finish(conn, str(row["id"]), "sent")
    logger.info(
        "notification sent",
        extra={"outbox_id": str(row["id"]), "provider": result.provider},
    )
    return True


def _finish(conn: Any, outbox_id: str, state: str) -> None:
    conn.execute(
        """
        update notification_outbox
        set state = %s, lease_expires_at = null
        where id = %s
        """,
        (state, outbox_id),
    )


def _retry_or_fail(conn: Any, row: dict[str, Any]) -> None:
    attempts = int(row["attempt_count"] or 0)
    if attempts >= MAX_ATTEMPTS:
        _finish(conn, str(row["id"]), "failed")
        return
    delay = min(2**attempts, 360) * 60
    conn.execute(
        """
        update notification_outbox
        set state = 'failed',
            next_attempt_at = now() + (%s * interval '1 second'),
            lease_expires_at = null
        where id = %s
        """,
        (delay, str(row["id"])),
    )


def apply_unsubscribe(conn: Any, *, user_id: str, purpose: str) -> None:
    if purpose.startswith("mute:"):
        company_id = purpose.split(":", 1)[1]
        conn.execute(
            """
            insert into notification_preferences (user_id, channel, frequency, muted_company_ids)
            values (%s, 'email', 'immediate', array[%s::uuid])
            on conflict (user_id) do update
              set muted_company_ids = (
                    select array_agg(distinct x)
                    from unnest(
                      notification_preferences.muted_company_ids || excluded.muted_company_ids
                    ) as x
                  ),
                  updated_at = now()
            """,
            (user_id, company_id),
        )
        return
    conn.execute(
        """
        insert into notification_preferences (user_id, channel, frequency)
        values (%s, 'email', 'unsubscribed')
        on conflict (user_id) do update
          set frequency = 'unsubscribed', updated_at = now()
        """,
        (user_id,),
    )
    email = _email_for_user(conn, user_id)
    if email:
        conn.execute(
            """
            insert into notification_suppressions (email_hash, reason)
            values (%s, 'unsubscribe')
            on conflict (email_hash) do nothing
            """,
            (email_hash(email),),
        )


def upsert_preference(conn: Any, *, user_id: str, frequency: str) -> None:
    if frequency not in {"immediate", "digest_weekly", "unsubscribed"}:
        raise NotifyError("invalid_frequency")
    conn.execute(
        """
        insert into notification_preferences (user_id, channel, frequency)
        values (%s, 'email', %s)
        on conflict (user_id) do update
          set frequency = excluded.frequency, updated_at = now()
        """,
        (user_id, frequency),
    )


def apply_provider_event(
    conn: Any,
    *,
    event_type: str,
    provider_event_id: str,
    provider_message_id: str,
    to_email: str,
) -> None:
    if not provider_event_id:
        raise NotifyError("invalid_webhook")
    replay = conn.execute(
        "select 1 from notification_deliveries where provider_event_id = %s",
        (provider_event_id,),
    ).fetchone()
    if replay:
        raise NotifyError("webhook_replay")
    state = "delivered"
    reason: str | None = None
    if "bounce" in event_type:
        state = "bounced"
        reason = "bounce"
    elif "complaint" in event_type:
        state = "complained"
        reason = "complaint"
    outbox_id = None
    if provider_message_id:
        match = conn.execute(
            """
            select outbox_id from notification_deliveries
            where provider_message_id = %s
            order by created_at desc
            limit 1
            """,
            (provider_message_id,),
        ).fetchone()
        if match and match["outbox_id"]:
            outbox_id = str(match["outbox_id"])
    if outbox_id:
        conn.execute(
            """
            insert into notification_deliveries (
              outbox_id, provider, provider_message_id, provider_event_id, state
            )
            values (%s, 'resend', %s, %s, %s)
            """,
            (outbox_id, provider_message_id or None, provider_event_id, state),
        )
        if reason:
            conn.execute(
                "update notification_outbox set state = 'suppressed' where id = %s",
                (outbox_id,),
            )
    if reason and to_email:
        conn.execute(
            """
            insert into notification_suppressions (email_hash, reason)
            values (%s, %s)
            on conflict (email_hash) do update set reason = excluded.reason
            """,
            (email_hash(to_email), reason),
        )


def notify_stats(conn: Any) -> dict[str, int]:
    def count(sql: str) -> int:
        row = conn.execute(sql).fetchone()
        return int(row["n"] if row else 0)

    lag = conn.execute(
        """
        select extract(epoch from (now() - min(created_at)))::int as age
        from notification_outbox
        where state in ('pending', 'claimed', 'failed')
        """
    ).fetchone()
    return {
        "fanout_pending": count(
            """
            select count(*) as n from notification_fanout_jobs
            where state in ('pending', 'running')
            """
        ),
        "outbox_pending": count(
            "select count(*) as n from notification_outbox where state in ('pending', 'claimed')"
        ),
        "sent": count("select count(*) as n from notification_outbox where state = 'sent'"),
        "suppressed": count(
            "select count(*) as n from notification_outbox where state = 'suppressed'"
        ),
        "failed": count("select count(*) as n from notification_outbox where state = 'failed'"),
        "lag_seconds": int(lag["age"] if lag and lag["age"] is not None else 0),
    }


def fixture_publish_change(conn: Any, *, slug: str, headline: str) -> str:
    if not fixture_delivery_enabled():
        raise NotifyError("fixture_disabled")
    from psycopg.types.json import Json

    ctx = conn.execute(
        """
        select c.id as company_id, s.id as source_id, snap.id as snapshot_id, snap.markdown
        from companies c
        join policy_sources s on s.company_id = c.id
        join snapshots snap on snap.id = s.current_snapshot_id
        where c.slug = %s
        limit 1
        """,
        (slug,),
    ).fetchone()
    if ctx is None:
        raise NotifyError("missing_company")
    markdown = str(ctx["markdown"] or "")
    quote = "We collect your email address to create an account."
    if quote not in markdown:
        raise NotifyError("missing_quote")
    event = conn.execute(
        """
        insert into change_events (
          company_id, source_id, from_snapshot, to_snapshot,
          materiality, headline, summary, quotes, publication_state
        )
        values (%s, %s, %s, %s, 'material', %s, 'Fixture published change.', %s, 'review_pending')
        returning id
        """,
        (
            str(ctx["company_id"]),
            str(ctx["source_id"]),
            str(ctx["snapshot_id"]),
            str(ctx["snapshot_id"]),
            headline[:200],
            Json([{"text": quote, "section": "Privacy"}]),
        ),
    ).fetchone()
    assert event is not None
    from privacyradar.publication import publish_event

    publish_event(conn, str(event["id"]), actor="cli:local")
    return str(event["id"])
