from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.catalog import load_catalog, seed_catalog
from privacyradar.catalog_ops import (
    CatalogError,
    health_report,
    record_request,
    validate_catalog,
    validate_companies,
)
from privacyradar.db import connect
from privacyradar.settings import settings
from privacyradar.testing.fixtures import make_company
from privacyradar.testing.persist import persist_company

pytestmark = pytest.mark.integration


def test_catalog_validate_rejects_duplicate_hosts() -> None:
    errors = validate_companies(
        [
            {
                "slug": "a",
                "name": "A",
                "website": "https://a.example.test",
                "category": "ai",
                "region": "global",
                "cohort": "seed",
                "privacy_url": "https://a.example.test/privacy",
            },
            {
                "slug": "b",
                "name": "B",
                "website": "https://b.example.test",
                "category": "ai",
                "region": "global",
                "cohort": "seed",
                "privacy_url": "https://a.example.test/privacy",
            },
        ]
    )
    assert any("duplicate" in item for item in errors)


def test_catalog_validate_rejects_ssrf_and_confusable_hosts() -> None:
    errors = validate_companies(
        [
            {
                "slug": "loop",
                "name": "Loop",
                "website": "https://loop.example.test",
                "category": "ai",
                "region": "global",
                "cohort": "seed",
                "privacy_url": "http://127.0.0.1/privacy",
            },
            {
                "slug": "one",
                "name": "One",
                "website": "https://modern.example.test",
                "category": "ai",
                "region": "global",
                "cohort": "seed",
                "privacy_url": "https://modern.example.test/privacy",
            },
            {
                "slug": "two",
                "name": "Two",
                "website": "https://rnodern.example.test",
                "category": "ai",
                "region": "global",
                "cohort": "seed",
                "privacy_url": "https://rnodern.example.test/privacy",
            },
        ]
    )
    assert any("SSRF" in item for item in errors)
    assert any("confusable" in item for item in errors)


def test_real_catalog_yaml_validates() -> None:
    assert validate_catalog() == []
    assert any(row["cohort"] == "c1" for row in load_catalog())


def test_seed_skips_disabled_cohort(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(
        "privacyradar.catalog.load_catalog",
        lambda: [
            {
                "slug": "seeded-co",
                "name": "Seeded",
                "website": "https://seeded.example.test",
                "category": "ai",
                "cohort": "seed",
                "region": "global",
                "privacy_url": "https://seeded.example.test/privacy",
            },
            {
                "slug": "later-co",
                "name": "Later",
                "website": "https://later.example.test",
                "category": "ai",
                "cohort": "c1",
                "region": "global",
                "privacy_url": "https://later.example.test/privacy",
            },
        ],
    )
    assert seed_catalog() == 1
    with connect() as conn:
        slugs = [row["slug"] for row in conn.execute("select slug from companies").fetchall()]
    assert slugs == ["seeded-co"]


def test_request_dedupes_existing_company_host(db_url: str) -> None:
    company = make_company(slug="signal", website="https://signal.org")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        persist_company(conn, company)
        first = record_request(
            conn, name="Signal", website="https://signal.org", category="messaging"
        )
        second = record_request(conn, name="Signal app", website="signal.org", category="messaging")
        other = record_request(
            conn, name="Not Signal", website="https://notsignal.org", category="messaging"
        )
        conn.commit()
        rows = conn.execute("select status from company_requests order by created_at").fetchall()
    assert first == "duplicate"
    assert second == "duplicate"
    assert other == "requested"
    assert [row["status"] for row in rows] == ["duplicate", "duplicate", "requested"]


def test_request_rejects_loopback_website(db_url: str) -> None:
    with (
        psycopg.connect(db_url, row_factory=dict_row) as conn,
        pytest.raises(CatalogError, match="invalid_website"),
    ):
        record_request(conn, name="Loop", website="http://127.0.0.1", category="ai")


def test_catalog_health_gate_is_stop_without_two_cycles(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        report = health_report(conn, record=True)
        conn.commit()
        again = health_report(conn, record=False)
    assert report["gate"] == "stop"
    assert "degraded" in report
    assert again["cycles_recorded"] == 1
    assert again["gate"] == "stop"


def test_catalog_health_gate_advances_after_two_passing_cycles(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """
            insert into catalog_health_snapshots (fetch_success_pct, evidence_valid_pct)
            values (95, 98), (99, 100)
            """
        )
        report = health_report(conn, record=False)
        conn.commit()
    assert report["gate"] == "advance"
    assert report["cycles_recorded"] == 2


def test_seed_catalog_skips_ssrf_urls(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(
        "privacyradar.catalog.load_catalog",
        lambda: [
            {
                "slug": "evil",
                "name": "Evil Co",
                "website": "https://evil.example.test",
                "category": "consumer",
                "cohort": "seed",
                "region": "global",
                "privacy_url": "http://127.0.0.1/privacy",
            }
        ],
    )
    assert seed_catalog() == 1
    with connect() as conn:
        companies = conn.execute("select slug from companies").fetchall()
        sources = conn.execute("select url from policy_sources").fetchall()
    assert [row["slug"] for row in companies] == ["evil"]
    assert sources == []
