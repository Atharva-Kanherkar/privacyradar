from __future__ import annotations

import ast
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.testing.fixtures import (
    EXAMPLE_EMAIL_DOMAIN,
    FROZEN_NOW,
    make_claim,
    make_company,
    make_follow,
    make_notification,
    make_observation,
    make_source,
    make_user,
)
from privacyradar.testing.persist import (
    FixturePersistenceUnsupported,
    persist_claim,
    persist_company,
    persist_follow,
    persist_notification,
    persist_observation,
    persist_source,
    persist_user,
    seed_public_fixtures,
)


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


def test_fixture_ids_are_stable_and_unique_per_key() -> None:
    first = make_company(slug="signal")
    again = make_company(slug="signal")
    other = make_company(slug="proton")
    assert first.id == again.id
    assert first.id != other.id
    assert make_user(handle="signal-tester").id == make_user(handle="signal-tester").id
    assert make_user(handle="signal-tester").id != make_user(handle="other-tester").id


def test_fixture_clock_is_frozen_by_default() -> None:
    company = make_company()
    source = make_source(company)
    observation = make_observation(source)
    user = make_user()
    follow = make_follow(user, company)
    notification = make_notification(user)
    assert company.created_at == FROZEN_NOW
    assert observation.fetched_at == FROZEN_NOW
    assert user.created_at == FROZEN_NOW
    assert follow.created_at == FROZEN_NOW
    assert notification.created_at == FROZEN_NOW
    assert user.email.endswith(f"@{EXAMPLE_EMAIL_DOMAIN}")


def test_fixture_module_does_not_import_live_clients() -> None:
    source = Path(__file__).resolve().parents[1] / "privacyradar" / "testing" / "fixtures.py"
    tree = ast.parse(source.read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])
    assert "httpx" not in imported
    assert "openai" not in imported


def test_testing_package_init_does_not_import_live_clients() -> None:
    source = Path(__file__).resolve().parents[1] / "privacyradar" / "testing" / "__init__.py"
    tree = ast.parse(source.read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("fakes" in module for module in imported)
    assert not any(module.startswith("httpx") or module.startswith("openai") for module in imported)


def test_fixture_persistence_round_trip(db_url: str) -> None:
    company = make_company(slug="roundtrip")
    source = make_source(company)
    observation = make_observation(source)
    claim = make_claim(observation, company)
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        persist_observation(conn, observation)
        persist_claim(conn, claim)
        conn.commit()
        row = conn.execute(
            """
            select c.slug, s.url, snap.doc_hash, x.model
            from companies c
            join policy_sources s on s.company_id = c.id
            join snapshots snap on snap.source_id = s.id
            join extractions x on x.snapshot_id = snap.id
            where c.slug = %s
            """,
            ("roundtrip",),
        ).fetchone()
    assert row is not None
    assert row["slug"] == "roundtrip"
    assert row["url"] == source.url
    assert row["doc_hash"] == observation.doc_hash
    assert row["model"] == "fake-model"


def test_fixture_isolation_hides_other_keys(db_url: str) -> None:
    company = make_company(slug="only-here")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        conn.commit()
        missing = conn.execute("select 1 from companies where slug = %s", ("other-key",)).fetchone()
        present = conn.execute(
            "select slug from companies where slug = %s", ("only-here",)
        ).fetchone()
    assert missing is None
    assert present is not None


def test_fixture_isolation_other_key_absent(db_url: str) -> None:
    company = make_company(slug="other-key")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        conn.commit()
        missing = conn.execute("select 1 from companies where slug = %s", ("only-here",)).fetchone()
        present = conn.execute(
            "select slug from companies where slug = %s", ("other-key",)
        ).fetchone()
    assert missing is None
    assert present is not None


def test_persist_user_round_trip(db_url: str) -> None:
    user = make_user(handle="roundtrip-user")
    company = make_company(slug="later")
    with _connect(db_url) as conn:
        persist_user(conn, user)
        conn.commit()
        row = conn.execute(
            """
            select u.email, p.region
            from auth_users u
            join consumer_profiles p on p.user_id = u.id
            where u.id = %s
            """,
            (str(user.id),),
        ).fetchone()
        persist_company(conn, company)
        persist_follow(conn, make_follow(user, company))
        conn.commit()
        watch = conn.execute(
            "select status from watches where user_id = %s",
            (str(user.id),),
        ).fetchone()
        seed_public_fixtures(conn)
        event = conn.execute(
            "select id from change_events where publication_state = 'published' limit 1"
        ).fetchone()
        assert event is not None
        persist_notification(conn, make_notification(user, event_id=event["id"]))
        conn.commit()
        boxed = conn.execute(
            "select state, channel from notification_outbox where user_id = %s",
            (str(user.id),),
        ).fetchone()
    assert row is not None
    assert row["email"] == user.email
    assert row["region"] == "US"
    assert watch is not None
    assert watch["status"] == "active"
    assert boxed is not None
    assert boxed["state"] == "pending"
    assert boxed["channel"] == "email"


def test_future_tables_are_in_memory_only(db_url: str) -> None:
    test_persist_user_round_trip(db_url)


def test_failed_observation_fixture_is_not_persisted_as_snapshot(db_url: str) -> None:
    company = make_company(slug="failed-obs")
    source = make_source(company)
    observation = make_observation(source, fetch_error="timeout")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        with pytest.raises(FixturePersistenceUnsupported, match="source_attempts"):
            persist_observation(conn, observation)


def test_seed_public_fixtures_is_idempotent(db_url: str) -> None:
    with _connect(db_url) as conn:
        assert seed_public_fixtures(conn) == 2
        conn.commit()
        assert seed_public_fixtures(conn) == 0
        count = conn.execute("select count(*) as n from companies").fetchone()
    assert count is not None
    assert count["n"] == 2
