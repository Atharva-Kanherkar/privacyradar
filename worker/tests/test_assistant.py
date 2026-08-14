from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.assistant import ask, identity_hash, run_eval
from privacyradar.testing.persist import seed_public_fixtures

pytestmark = pytest.mark.integration


def _enable(conn: psycopg.Connection[dict[str, object]]) -> None:
    conn.execute("update product_switches set enabled = true where key = 'assistant'")


def test_assistant_disabled_does_not_answer(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        conn.commit()
        payload = ask(
            conn,
            slug="signal",
            question="Does Signal collect email addresses?",
            identity=identity_hash("tester-off"),
        )
    assert payload["status"] == "disabled"
    assert payload["text"] == ""
    assert payload["citations"] == []


def test_assistant_answers_only_with_published_quote(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        _enable(conn)
        conn.commit()
        payload = ask(
            conn,
            slug="signal",
            question="Does Signal collect email addresses?",
            identity=identity_hash("tester-on"),
        )
    assert payload["status"] == "answered"
    assert payload["citations"]
    assert "email" in payload["citations"][0]["quote"].lower()
    assert "We found published evidence" in payload["text"]


def test_assistant_refuses_without_citation(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        _enable(conn)
        conn.commit()
        payload = ask(
            conn,
            slug="signal",
            question="What is the weather in Berlin?",
            identity=identity_hash("tester-weather"),
        )
    assert payload["status"] == "refused"
    assert payload["citations"] == []
    assert payload["text"] == ""


def test_assistant_isolates_company_retrieval(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        _enable(conn)
        conn.commit()
        payload = ask(
            conn,
            slug="signal",
            question="Do you share information with advertising partners?",
            identity=identity_hash("tester-iso"),
        )
    assert payload["status"] == "refused"
    assert payload["citations"] == []


def test_assistant_rate_limit(db_url: str) -> None:
    identity = identity_hash("tester-limit")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        _enable(conn)
        conn.commit()
        last = None
        for _ in range(11):
            last = ask(
                conn,
                slug="signal",
                question="Does Signal collect email addresses?",
                identity=identity,
            )
        conn.commit()
    assert last is not None
    assert last["status"] == "rate_limited"


def test_eval_assistant_gates_pass_on_golden_fake(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        conn.commit()
        report = run_eval(conn)
    assert report["gate"] == "pass"
    assert report["answered"] >= 1
    assert report["refused"] >= 1
    assert report["mismatches"] == 0
