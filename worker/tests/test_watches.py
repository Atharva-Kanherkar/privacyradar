from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.consumer import delete_consumer
from privacyradar.testing.fixtures import make_company, make_follow, make_user
from privacyradar.testing.persist import (
    persist_company,
    persist_follow,
    persist_user,
    seed_public_fixtures,
)
from privacyradar.watches import (
    WatchError,
    follow,
    list_active_watches,
    list_radar_events,
    session_user_id,
    unfollow,
)


def test_follow_rejects_missing_session_identity() -> None:
    with pytest.raises(WatchError, match="missing session"):
        session_user_id(session_user_id=None, body={"slug": "signal"})
    with pytest.raises(WatchError, match="user id must come from session"):
        session_user_id(session_user_id="sess", body={"userId": "attacker"})
    with pytest.raises(WatchError, match="user id must come from session"):
        session_user_id(session_user_id="sess", body={"user_id": "attacker"})
    assert session_user_id(session_user_id="sess", body={"slug": "signal"}) == "sess"


def test_follow_is_idempotent_for_same_user_company(db_url: str) -> None:
    user = make_user(handle="watcher")
    company = make_company(slug="watch-co")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        persist_user(conn, user)
        persist_company(conn, company)
        follow(conn, user_id=str(user.id), company_id=str(company.id), source="company_page")
        with pytest.raises(WatchError, match="invalid source"):
            follow(conn, user_id=str(user.id), company_id=str(company.id), source="email")
        follow(conn, user_id=str(user.id), company_id=str(company.id), source="resume")
        conn.commit()
        rows = conn.execute(
            "select status, source from watches where user_id = %s and company_id = %s",
            (str(user.id), str(company.id)),
        ).fetchall()
        active = list_active_watches(conn, user_id=str(user.id))
        events = conn.execute(
            "select count(*) as n from product_events where user_id = %s and name = 'follow'",
            (str(user.id),),
        ).fetchone()
    assert len(rows) == 1
    assert rows[0]["status"] == "active"
    assert rows[0]["source"] == "resume"
    assert len(active) == 1
    assert active[0]["slug"] == "watch-co"
    assert events is not None and events["n"] == 2


def test_unfollow_hides_company_from_radar(db_url: str) -> None:
    user = make_user(handle="unfollower")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id = conn.execute(
            "select id from companies where slug = 'signal'"
        ).fetchone()
        assert company_id is not None
        follow(
            conn,
            user_id=str(user.id),
            company_id=str(company_id["id"]),
            source="company_page",
        )
        conn.commit()
        before = list_radar_events(conn, user_id=str(user.id))
        unfollow(conn, user_id=str(user.id), company_id=str(company_id["id"]))
        conn.commit()
        after = list_radar_events(conn, user_id=str(user.id))
    assert any(row["headline"] == "PUBLISHED_FIXTURE_HEADLINE" for row in before)
    assert not any(row["headline"] == "PUBLISHED_FIXTURE_HEADLINE" for row in after)
    assert not any(row["headline"] == "UNPUBLISHED_FIXTURE_HEADLINE" for row in before)


def test_radar_lists_only_published_followed_changes(db_url: str) -> None:
    test_unfollow_hides_company_from_radar(db_url)


def test_user_cannot_read_another_users_watches(db_url: str) -> None:
    owner = make_user(handle="owner")
    other = make_user(handle="other")
    company = make_company(slug="private-watch")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        persist_user(conn, owner)
        persist_user(conn, other)
        persist_company(conn, company)
        follow(
            conn,
            user_id=str(owner.id),
            company_id=str(company.id),
            source="company_page",
        )
        conn.commit()
        visible = list_radar_events(conn, user_id=str(other.id))
        stolen = conn.execute(
            "select 1 from watches where user_id = %s",
            (str(owner.id),),
        ).fetchone()
    assert visible == []
    assert stolen is not None


def test_delete_account_removes_watches_keeps_publications(db_url: str) -> None:
    user = make_user(handle="watch-deleter")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        persist_user(conn, user)
        company_id = conn.execute(
            "select id from companies where slug = 'signal'"
        ).fetchone()
        assert company_id is not None
        follow(
            conn,
            user_id=str(user.id),
            company_id=str(company_id["id"]),
            source="company_page",
        )
        conn.commit()
        before = conn.execute("select count(*) as n from published_claims").fetchone()
        delete_consumer(conn, str(user.id))
        conn.commit()
        watches = conn.execute(
            "select 1 from watches where user_id = %s",
            (str(user.id),),
        ).fetchone()
        after = conn.execute("select count(*) as n from published_claims").fetchone()
    assert watches is None
    assert after is not None and before is not None and after["n"] == before["n"]


def test_persist_follow_round_trip(db_url: str) -> None:
    user = make_user(handle="persist-follow")
    company = make_company(slug="persist-follow-co")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        persist_user(conn, user)
        persist_company(conn, company)
        persist_follow(conn, make_follow(user, company))
        conn.commit()
        row = conn.execute(
            "select status from watches where user_id = %s and company_id = %s",
            (str(user.id), str(company.id)),
        ).fetchone()
    assert row is not None
    assert row["status"] == "active"
