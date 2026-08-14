from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Json

from privacyradar.consumer import delete_consumer
from privacyradar.notify import (
    apply_provider_event,
    apply_unsubscribe,
    enqueue_fanout,
    fixture_publish_change,
    notify_stats,
    run_deliver,
    run_fanout,
    upsert_preference,
)
from privacyradar.notify_mail import (
    NotifyError,
    email_hash,
    get_provider,
    render_alert,
    sign_unsub_token,
    verify_svix_signature,
    verify_unsub_token,
)
from privacyradar.publication import publish_event
from privacyradar.settings import settings
from privacyradar.testing.fixtures import make_notification, make_user
from privacyradar.testing.persist import persist_notification, persist_user, seed_public_fixtures
from privacyradar.watches import follow

QUOTE = "We collect your email address to create an account."


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


@pytest.fixture(autouse=True)
def _notify_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_secret", "test-notify-secret")
    monkeypatch.setattr(settings, "notify_provider", "fake")
    monkeypatch.setattr(settings, "notify_signing_key", "")
    monkeypatch.setattr(settings, "public_base_url", "http://127.0.0.1:3000")
    monkeypatch.setenv("AUTH_DELIVERY", "fixture")
    monkeypatch.setenv("AUTH_SECRET", "test-notify-secret")


def _signal_ids(conn: psycopg.Connection[dict[str, object]]) -> tuple[str, str, str]:
    row = conn.execute(
        """
        select c.id as company_id, s.id as source_id, snap.id as snapshot_id
        from companies c
        join policy_sources s on s.company_id = c.id
        join snapshots snap on snap.id = s.current_snapshot_id
        where c.slug = 'signal'
        """
    ).fetchone()
    assert row is not None
    return str(row["company_id"]), str(row["source_id"]), str(row["snapshot_id"])


def _pending_event(conn: psycopg.Connection[dict[str, object]], headline: str) -> str:
    company_id, source_id, snapshot_id = _signal_ids(conn)
    event = conn.execute(
        """
        insert into change_events (
          company_id, source_id, from_snapshot, to_snapshot,
          materiality, headline, summary, quotes, publication_state
        )
        values (%s, %s, %s, %s, 'material', %s, 's', %s, 'review_pending')
        returning id
        """,
        (company_id, source_id, snapshot_id, snapshot_id, headline, Json([{"text": QUOTE}])),
    ).fetchone()
    assert event is not None
    return str(event["id"])


def test_enqueue_fanout_skips_unpublished_and_non_material(db_url: str) -> None:
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        pending = conn.execute(
            """
            select id from change_events
            where publication_state = 'review_pending'
            limit 1
            """
        ).fetchone()
        assert pending is not None
        assert enqueue_fanout(conn, str(pending["id"])) is None
        company_id, source_id, snapshot_id = _signal_ids(conn)
        cosmetic = conn.execute(
            """
            insert into change_events (
              company_id, source_id, from_snapshot, to_snapshot,
              materiality, headline, summary, publication_state
            )
            values (%s, %s, %s, %s, 'cosmetic', 'n', 's', 'published')
            returning id
            """,
            (company_id, source_id, snapshot_id, snapshot_id),
        ).fetchone()
        assert cosmetic is not None
        assert enqueue_fanout(conn, str(cosmetic["id"])) is None
        conn.commit()


def test_publish_event_inserts_one_fanout_job_not_outbox_rows(db_url: str) -> None:
    user = make_user(handle="fanout-job")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Held for notify")
        publish_event(conn, event_id, actor="cli:local")
        conn.commit()
        jobs = conn.execute(
            "select count(*) as n from notification_fanout_jobs where event_id = %s",
            (event_id,),
        ).fetchone()
        outbox = conn.execute(
            "select count(*) as n from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
    assert jobs is not None and jobs["n"] == 1
    assert outbox is not None and outbox["n"] == 0


def test_outbox_unique_survives_crash_replay(db_url: str) -> None:
    user = make_user(handle="replay")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Replay change")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        run_fanout(conn)
        conn.commit()
        rows = conn.execute(
            "select count(*) as n from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
    assert rows is not None and rows["n"] == 1


def test_concurrent_fanout_does_not_duplicate_outbox(db_url: str) -> None:
    user = make_user(handle="concurrent")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Concurrent change")
        publish_event(conn, event_id, actor="cli:local")
        conn.commit()

    def work(_: int) -> None:
        with _connect(db_url) as conn:
            run_fanout(conn)
            conn.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(work, [1, 2]))
    with _connect(db_url) as conn:
        rows = conn.execute(
            "select count(*) as n from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
    assert rows is not None and rows["n"] == 1


def test_preferences_applied_before_fanout_and_before_send(db_url: str) -> None:
    user = make_user(handle="prefs")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        upsert_preference(conn, user_id=str(user.id), frequency="unsubscribed")
        event_id = _pending_event(conn, "Muted change")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        before = conn.execute(
            "select count(*) as n from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
        upsert_preference(conn, user_id=str(user.id), frequency="immediate")
        event_id2 = _pending_event(conn, "Later change")
        publish_event(conn, event_id2, actor="cli:local")
        run_fanout(conn)
        conn.execute(
            "update notification_preferences set frequency = 'unsubscribed' where user_id = %s",
            (str(user.id),),
        )
        sent = run_deliver(conn)
        conn.commit()
        inbox = conn.execute("select count(*) as n from notification_fixture_inbox").fetchone()
    assert before is not None and before["n"] == 0
    assert sent == 0
    assert inbox is not None and inbox["n"] == 0


def test_unfollow_before_send_cancels_outbox(db_url: str) -> None:
    from privacyradar.watches import unfollow

    user = make_user(handle="unfollowed")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Then unfollowed")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        unfollow(conn, user_id=str(user.id), company_id=company_id)
        sent = run_deliver(conn)
        conn.commit()
        row = conn.execute(
            "select state from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
    assert sent == 0
    assert row is not None and row["state"] == "cancelled"


def test_signed_unsubscribe_rejects_tampering_and_expiry() -> None:
    token = sign_unsub_token(user_id="user-1", secret="test-notify-secret")
    parsed = verify_unsub_token(token, secret="test-notify-secret")
    assert parsed["user_id"] == "user-1"
    with pytest.raises(NotifyError, match="invalid_token"):
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        verify_unsub_token(tampered, secret="test-notify-secret")
    expired = sign_unsub_token(
        user_id="user-1",
        secret="test-notify-secret",
        exp=int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
    )
    with pytest.raises(NotifyError, match="expired_token"):
        verify_unsub_token(expired, secret="test-notify-secret")


def test_render_alert_has_html_and_text_without_images() -> None:
    token = sign_unsub_token(user_id="user-1", secret="test-notify-secret")
    rendered = render_alert(
        company_name="Signal",
        headline="New sharing language",
        summary="A published change.",
        event_id="11111111-1111-1111-1111-111111111111",
        kind="publish",
        unsubscribe_token=token,
        data_types_added=["email"],
    )
    assert "New sharing language" in rendered.subject
    assert "Signal" in rendered.text
    assert "/changes/11111111-1111-1111-1111-111111111111" in rendered.text
    assert "/radar/settings" in rendered.text
    assert "/unsubscribe?token=" in rendered.text
    assert "<img" not in rendered.html.lower()
    assert rendered.html.startswith("<!doctype html>")


def test_webhook_rejects_bad_signature_and_replay(db_url: str) -> None:
    body = (
        b'{"type":"email.bounced","data":'
        b'{"email_id":"msg_1","to":["a@fixtures.privacyradar.test"]}}'
    )
    with pytest.raises(NotifyError, match="invalid_webhook"):
        verify_svix_signature(
            secret="whsec_dGVzdA==",
            body=body,
            svix_id="msg_1",
            svix_timestamp=str(int(datetime.now(UTC).timestamp())),
            svix_signature="v1,not-a-real-signature",
        )
    with _connect(db_url) as conn:
        apply_provider_event(
            conn,
            event_type="email.bounced",
            provider_event_id="evt_1",
            provider_message_id="msg_1",
            to_email="a@fixtures.privacyradar.test",
        )
        conn.commit()
        with pytest.raises(NotifyError, match="webhook_replay"):
            apply_provider_event(
                conn,
                event_type="email.bounced",
                provider_event_id="evt_1",
                provider_message_id="msg_1",
                to_email="a@fixtures.privacyradar.test",
            )


def test_bounce_and_complaint_suppress_future_sends(db_url: str) -> None:
    user = make_user(handle="bounced")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        apply_provider_event(
            conn,
            event_type="email.bounced",
            provider_event_id="evt_bounce",
            provider_message_id="",
            to_email=user.email,
        )
        event_id = _pending_event(conn, "After bounce")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        sent = run_deliver(conn)
        conn.commit()
        boxed = conn.execute(
            "select count(*) as n from notification_outbox where event_id = %s",
            (event_id,),
        ).fetchone()
        suppressed = conn.execute(
            "select reason from notification_suppressions where email_hash = %s",
            (email_hash(user.email),),
        ).fetchone()
    assert sent == 0
    assert boxed is not None and boxed["n"] == 0
    assert suppressed is not None and suppressed["reason"] == "bounce"


def test_fake_provider_never_calls_resend(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    def boom(*_args: object, **_kwargs: object) -> object:
        called.append(1)
        raise AssertionError("resend must not be called")

    monkeypatch.setattr("privacyradar.notify_mail.httpx.post", boom)

    class _Conn:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            return None

    get_provider().send(
        _Conn(),
        to_email="a@fixtures.privacyradar.test",
        rendered=render_alert(
            company_name="Signal",
            headline="h",
            summary="s",
            event_id="11111111-1111-1111-1111-111111111111",
            kind="publish",
            unsubscribe_token="t",
        ),
    )
    assert called == []
    assert get_provider().__class__.__name__ == "FakeProvider"


def test_published_change_sends_one_eligible_email_via_fake_provider(db_url: str) -> None:
    user = make_user(handle="eligible")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "E2E_WORKER_HEADLINE")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        first = run_deliver(conn)
        second = run_deliver(conn)
        conn.commit()
        inbox = conn.execute(
            """
            select subject, body_text from notification_fixture_inbox
            where email_hash = %s
            """,
            (email_hash(user.email),),
        ).fetchall()
        stats = notify_stats(conn)
    assert first == 1
    assert second == 0
    assert len(inbox) == 1
    assert "E2E_WORKER_HEADLINE" in inbox[0]["subject"]
    assert "E2E_WORKER_HEADLINE" in inbox[0]["body_text"]
    assert "/changes/" in inbox[0]["body_text"]
    assert "UNPUBLISHED_FIXTURE_HEADLINE" not in inbox[0]["body_text"]
    assert stats["sent"] == 1


def test_correction_enqueues_follow_up_revision(db_url: str) -> None:
    user = make_user(handle="corrected")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Original alert")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        run_deliver(conn)
        enqueue_fanout(conn, event_id, kind="correction")
        conn.execute(
            "update change_events set publication_state = 'corrected' where id = %s",
            (event_id,),
        )
        run_fanout(conn)
        run_deliver(conn)
        conn.commit()
        rows = conn.execute(
            """
            select revision, kind, state
            from notification_outbox
            where event_id = %s
            order by revision
            """,
            (event_id,),
        ).fetchall()
        inbox = conn.execute(
            """
            select subject from notification_fixture_inbox
            where email_hash = %s
            order by created_at
            """,
            (email_hash(user.email),),
        ).fetchall()
    assert [row["revision"] for row in rows] == [1, 2]
    assert rows[1]["kind"] == "correction"
    assert rows[1]["state"] == "sent"
    assert len(inbox) == 2
    assert "Correction" in inbox[1]["subject"]


def test_notifications_switch_off_skips_send(db_url: str) -> None:
    user = make_user(handle="switched")
    with _connect(db_url) as conn:
        try:
            seed_public_fixtures(conn)
            persist_user(conn, user)
            company_id, _, _ = _signal_ids(conn)
            follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
            conn.execute("update product_switches set enabled = false where key = 'notifications'")
            event_id = _pending_event(conn, "Switch off")
            publish_event(conn, event_id, actor="cli:local")
            jobs = conn.execute(
                "select count(*) as n from notification_fanout_jobs where event_id = %s",
                (event_id,),
            ).fetchone()
            sent = run_deliver(conn)
            conn.commit()
        finally:
            conn.execute("update product_switches set enabled = true where key = 'notifications'")
            conn.commit()
    assert jobs is not None and jobs["n"] == 0
    assert sent == 0


def test_delete_account_removes_notification_rows_keeps_publications(db_url: str) -> None:
    user = make_user(handle="deleter")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "Then deleted")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        run_deliver(conn)
        delete_consumer(conn, str(user.id))
        conn.commit()
        prefs = conn.execute(
            "select count(*) as n from notification_preferences where user_id = %s",
            (str(user.id),),
        ).fetchone()
        boxed = conn.execute(
            "select count(*) as n from notification_outbox where user_id = %s",
            (str(user.id),),
        ).fetchone()
        published = conn.execute(
            "select count(*) as n from change_events where id = %s",
            (event_id,),
        ).fetchone()
    assert prefs is not None and prefs["n"] == 0
    assert boxed is not None and boxed["n"] == 0
    assert published is not None and published["n"] == 1


def test_persist_notification_round_trip(db_url: str) -> None:
    user = make_user(handle="persist-note")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        event = conn.execute(
            "select id from change_events where publication_state = 'published' limit 1"
        ).fetchone()
        assert event is not None
        persist_notification(conn, make_notification(user, event_id=UUID(str(event["id"]))))
        conn.commit()
        row = conn.execute(
            "select channel, state from notification_outbox where user_id = %s",
            (str(user.id),),
        ).fetchone()
    assert row is not None
    assert row["channel"] == "email"
    assert row["state"] == "pending"


def test_fixture_publish_change_requires_fixture_delivery(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AUTH_DELIVERY", raising=False)
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        with pytest.raises(NotifyError, match="fixture_disabled"):
            fixture_publish_change(conn, slug="signal", headline="nope")


def test_apply_unsubscribe_blocks_later_mail(db_url: str) -> None:
    user = make_user(handle="unsubbed")
    with _connect(db_url) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        apply_unsubscribe(conn, user_id=str(user.id), purpose="unsub")
        company_id, _, _ = _signal_ids(conn)
        follow(conn, user_id=str(user.id), company_id=company_id, source="company_page")
        event_id = _pending_event(conn, "After unsub")
        publish_event(conn, event_id, actor="cli:local")
        run_fanout(conn)
        sent = run_deliver(conn)
        conn.commit()
    assert sent == 0
