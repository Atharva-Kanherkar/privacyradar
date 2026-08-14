from __future__ import annotations

import hashlib

import psycopg
from psycopg.rows import dict_row

from privacyradar.auth_helpers import email_hash, safe_callback_url
from privacyradar.consumer import delete_consumer
from privacyradar.publication import publish_stats
from privacyradar.testing.fixtures import make_user
from privacyradar.testing.persist import persist_user, seed_public_fixtures


def test_callback_url_rejects_absolute_and_protocol_relative() -> None:
    assert safe_callback_url("/account") == "/account"
    assert safe_callback_url("/companies/signal") == "/companies/signal"
    assert safe_callback_url("https://evil.test") == "/account"
    assert safe_callback_url("//evil.test") == "/account"
    assert safe_callback_url("/\\evil.test") == "/account"
    assert safe_callback_url("/account@evil.test") == "/account"
    assert safe_callback_url(None) == "/account"
    assert safe_callback_url("") == "/account"


def test_email_hash_not_equal_to_email() -> None:
    email = "Signal-Tester@fixtures.privacyradar.test"
    digest = email_hash(email)
    assert digest != email
    assert digest == hashlib.sha256(b"signal-tester@fixtures.privacyradar.test").hexdigest()
    assert email_hash(" SIGNAL-TESTER@fixtures.privacyradar.test ") == digest


def test_magic_link_request_does_not_reveal_account() -> None:
    known = "If that address can be used, we sent a link."
    unknown = "If that address can be used, we sent a link."
    assert known == unknown


def test_delete_account_removes_profile_keeps_publications(db_url: str) -> None:
    user = make_user(handle="deleter")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        conn.execute(
            "insert into auth_magic_inbox (email_hash, url) values (%s, %s)",
            (email_hash(user.email), "/api/auth/magic-link/verify?token=old&callbackURL=/account"),
        )
        conn.commit()
        before = conn.execute("select count(*) as n from published_claims").fetchone()
        assert before is not None and before["n"] >= 1
        delete_consumer(conn, str(user.id))
        conn.commit()
        profile = conn.execute(
            "select 1 from consumer_profiles where user_id = %s",
            (str(user.id),),
        ).fetchone()
        auth_user = conn.execute(
            "select 1 from auth_users where id = %s",
            (str(user.id),),
        ).fetchone()
        sessions = conn.execute(
            "select 1 from auth_sessions where user_id = %s",
            (str(user.id),),
        ).fetchone()
        accounts = conn.execute(
            "select 1 from auth_accounts where user_id = %s",
            (str(user.id),),
        ).fetchone()
        inbox = conn.execute(
            "select 1 from auth_magic_inbox where email_hash = %s",
            (email_hash(user.email),),
        ).fetchone()
        after = conn.execute("select count(*) as n from published_claims").fetchone()
        deleted = conn.execute(
            """
            select action from consent_events
            where user_id = %s
            order by created_at
            """,
            (str(user.id),),
        ).fetchall()
    assert profile is None
    assert auth_user is None
    assert sessions is None
    assert accounts is None
    assert inbox is None
    assert after is not None and after["n"] == before["n"]
    assert [row["action"] for row in deleted][-2:] == ["delete_requested", "deleted"]


def test_fixture_inbox_stores_link_not_plaintext_token_in_logs(db_url: str) -> None:
    email = "inbox-user@fixtures.privacyradar.test"
    token = "plaintext-magic-token"
    url = f"/api/auth/magic-link/verify?token={token}&callbackURL=/account"
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            "insert into auth_magic_inbox (email_hash, url) values (%s, %s)",
            (email_hash(email), url),
        )
        conn.commit()
        row = conn.execute(
            "select email_hash, url from auth_magic_inbox where email_hash = %s",
            (email_hash(email),),
        ).fetchone()
        stats = publish_stats(conn)
    assert row is not None
    assert row["email_hash"] != email
    assert email not in row["email_hash"]
    assert "inbox-user" not in row["email_hash"]
    dumped = str(stats)
    assert token not in dumped
    assert email not in dumped
    assert "AUTH_SECRET" not in dumped
