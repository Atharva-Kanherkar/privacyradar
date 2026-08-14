from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.migrate import MigrationError, discover_migrations, migrate

pytestmark = pytest.mark.integration

REQUIRED_TABLES = {
    "companies",
    "policy_sources",
    "snapshots",
    "extractions",
    "change_events",
    "schema_migrations",
    "source_attempts",
    "observations",
    "document_changes",
    "fetch_jobs",
    "source_operator_actions",
    "taxonomy_versions",
    "extraction_runs",
    "candidate_claims",
    "evidence_spans",
    "publication_revisions",
    "published_claims",
    "review_actions",
    "corrections",
    "product_switches",
    "auth_users",
    "auth_sessions",
    "auth_accounts",
    "auth_verifications",
    "consumer_profiles",
    "consent_events",
    "auth_magic_inbox",
    "watches",
    "product_events",
    "notification_preferences",
    "notification_fanout_jobs",
    "notification_outbox",
    "notification_deliveries",
    "notification_suppressions",
    "notification_fixture_inbox",
    "catalog_cohorts",
    "company_requests",
    "catalog_health_snapshots",
    "assistant_usage",
}

INITIAL_CHECKSUM = "5957a7874aaec1741621bfae3fff13f08fc3ca0c9222bb4592e56eac61cb3c8e"
HEAD_VERSIONS = [
    "0001",
    "0002",
    "0003",
    "0004",
    "0005",
    "0006",
    "0007",
    "0008",
    "0009",
    "0010",
    "0011",
]


def _tables(url: str) -> set[str]:
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public' and table_type = 'BASE TABLE'
            """
        ).fetchall()
    return {row[0] for row in rows}


def _ledger(url: str) -> list[tuple[str, str]]:
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "select version, checksum from schema_migrations order by version"
        ).fetchall()
    return [(row[0], row[1]) for row in rows]


def test_migrate_fresh_database_to_head(empty_database_url: str) -> None:
    applied = migrate(empty_database_url)
    assert applied == HEAD_VERSIONS
    assert _tables(empty_database_url) >= REQUIRED_TABLES
    ledger = _ledger(empty_database_url)
    assert [row[0] for row in ledger] == HEAD_VERSIONS
    assert len(ledger) == 11
    assert ledger[0][1] == INITIAL_CHECKSUM


def test_migrate_fresh_includes_0004(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0011(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0010(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0009(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0008(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0007(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0006(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_fresh_includes_0005(empty_database_url: str) -> None:
    test_migrate_fresh_database_to_head(empty_database_url)


def test_migrate_is_idempotent(empty_database_url: str) -> None:
    first = migrate(empty_database_url)
    tables_after_first = _tables(empty_database_url)
    ledger_after_first = _ledger(empty_database_url)
    second = migrate(empty_database_url)
    assert first == HEAD_VERSIONS
    assert second == []
    assert _tables(empty_database_url) == tables_after_first
    assert _ledger(empty_database_url) == ledger_after_first


def test_migrate_rejects_checksum_mismatch(empty_database_url: str) -> None:
    migrate(empty_database_url)
    with psycopg.connect(empty_database_url) as conn:
        conn.execute(
            "update schema_migrations set checksum = %s where version = %s",
            ("0" * 64, "0001"),
        )
        conn.commit()
        conn.execute(
            """
            insert into companies (slug, name, website)
            values ('kept', 'Kept Co', 'https://kept.example.test')
            """
        )
        conn.commit()

    with pytest.raises(MigrationError, match="checksum mismatch"):
        migrate(empty_database_url)

    with psycopg.connect(empty_database_url) as conn:
        count = conn.execute("select count(*) from companies").fetchone()
        assert count is not None
        assert count[0] == 1


def test_migrate_failed_file_does_not_record_version(
    empty_database_url: str, tmp_path: Path
) -> None:
    initial = Path(__file__).resolve().parents[2] / "db" / "migrations" / "0001_initial.sql"
    (tmp_path / "0001_initial.sql").write_bytes(initial.read_bytes())
    (tmp_path / "0002_bad.sql").write_text("create table ok_marker (id int);\nselect 1/0;\n")

    with pytest.raises(MigrationError, match="0002_bad"):
        migrate(empty_database_url, migrations_dir=tmp_path)

    assert "ok_marker" not in _tables(empty_database_url)
    assert _ledger(empty_database_url) == [("0001", discover_migrations(tmp_path)[0].checksum)]


def test_migrate_upgrades_prototype_schema_preserving_rows(empty_database_url: str) -> None:
    schema = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
    with psycopg.connect(
        empty_database_url, cursor_factory=psycopg.ClientCursor, autocommit=True
    ) as conn:
        conn.execute(schema.read_text())
        conn.execute(
            """
            insert into companies (id, slug, name, website, category)
            values (
              '11111111-1111-1111-1111-111111111111',
              'prototype',
              'Prototype Co',
              'https://prototype.example.test',
              'consumer'
            )
            """
        )
        conn.execute(
            """
            insert into policy_sources (id, company_id, kind, url, region)
            values (
              '22222222-2222-2222-2222-222222222222',
              '11111111-1111-1111-1111-111111111111',
              'privacy',
              'https://prototype.example.test/privacy',
              'global'
            )
            """
        )
        conn.execute(
            """
            insert into snapshots (
              id, source_id, http_status, content_type, raw_html, markdown,
              doc_hash, section_hashes
            )
            values (
              '33333333-3333-3333-3333-333333333333',
              '22222222-2222-2222-2222-222222222222',
              200,
              'text/html',
              '<p>policy</p>',
              '# Privacy\nWe collect your email address to create an account.',
              'abc123',
              '{}'::jsonb
            )
            """
        )

    applied = migrate(empty_database_url)
    assert applied == HEAD_VERSIONS
    with psycopg.connect(empty_database_url) as conn:
        company = conn.execute(
            "select slug, name from companies where id = %s",
            ("11111111-1111-1111-1111-111111111111",),
        ).fetchone()
        snapshot = conn.execute(
            "select doc_hash, is_valid from snapshots where id = %s",
            ("33333333-3333-3333-3333-333333333333",),
        ).fetchone()
        observation = conn.execute(
            "select count(*) from observations where snapshot_id = %s",
            ("33333333-3333-3333-3333-333333333333",),
        ).fetchone()
        pointer = conn.execute(
            "select current_snapshot_id from policy_sources where id = %s",
            ("22222222-2222-2222-2222-222222222222",),
        ).fetchone()
        assert company is not None
        assert company[0] == "prototype"
        assert snapshot is not None
        assert snapshot[0] == "abc123"
        assert snapshot[1] is True
        assert observation is not None
        assert observation[0] == 1
        assert pointer is not None
        assert str(pointer[0]) == "33333333-3333-3333-3333-333333333333"
    assert [row[0] for row in _ledger(empty_database_url)] == HEAD_VERSIONS


def test_migrate_0001_database_backfills_valid_and_invalid_snapshots(
    empty_database_url: str,
) -> None:
    initial = Path(__file__).resolve().parents[2] / "db" / "migrations" / "0001_initial.sql"
    with psycopg.connect(
        empty_database_url, cursor_factory=psycopg.ClientCursor, autocommit=True
    ) as conn:
        conn.execute(initial.read_text())
        conn.execute(
            """
            insert into companies (id, slug, name, website)
            values (
              'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
              'legacy',
              'Legacy Co',
              'https://legacy.example.test'
            )
            """
        )
        conn.execute(
            """
            insert into policy_sources (id, company_id, url)
            values (
              'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
              'https://legacy.example.test/privacy'
            )
            """
        )
        conn.execute(
            """
            insert into snapshots (
              id, source_id, http_status, content_type, raw_html, markdown,
              doc_hash, section_hashes, fetch_error
            )
            values (
              'cccccccc-cccc-cccc-cccc-cccccccccccc',
              'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              200,
              'text/html',
              '<p>ok</p>',
              '# Privacy\nWe collect your email address to create an account.',
              'validhash',
              '{}'::jsonb,
              null
            ), (
              'dddddddd-dddd-dddd-dddd-dddddddddddd',
              'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              0,
              '',
              '',
              '',
              'empty',
              '{}'::jsonb,
              'timeout'
            )
            """
        )

    applied = migrate(empty_database_url)
    assert "0002" in applied
    from privacyradar.reconcile import reconcile_observations

    with psycopg.connect(empty_database_url, row_factory=dict_row) as conn:
        first = reconcile_observations(conn)
        conn.commit()
        second = reconcile_observations(conn)
        conn.commit()
        valid = conn.execute("select is_valid, id from snapshots").fetchall()
        current = conn.execute(
            "select current_snapshot_id, health_status from policy_sources"
        ).fetchone()
        attempts = conn.execute("select status, error_code from source_attempts").fetchall()
        observations = conn.execute("select count(*) as n from observations").fetchone()
    assert first.observations_created == 0
    assert first.attempts_created == 0
    assert second.observations_created == 0
    assert second.attempts_created == 0
    assert second.current_pointers_set == 0
    valid_map = {str(row["id"]): row["is_valid"] for row in valid}
    assert valid_map["cccccccc-cccc-cccc-cccc-cccccccccccc"] is True
    assert valid_map["dddddddd-dddd-dddd-dddd-dddddddddddd"] is False
    assert current is not None
    assert str(current["current_snapshot_id"]) == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert current["health_status"] == "healthy"
    assert observations is not None and observations["n"] == 1
    statuses = {row["status"] for row in attempts}
    assert "succeeded" in statuses
    assert "failed" in statuses
    failed_codes = {row["error_code"] for row in attempts if row["status"] == "failed"}
    assert failed_codes == {"timeout"}
    with psycopg.connect(empty_database_url, row_factory=dict_row) as conn:
        due = conn.execute("select due_at, current_snapshot_id from policy_sources").fetchone()
        jobs = conn.execute("select count(*) as n from fetch_jobs").fetchone()
    assert due is not None
    assert due["due_at"] is not None
    assert str(due["current_snapshot_id"]) == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert jobs is not None and jobs["n"] == 0


def test_migrate_0002_database_upgrades_to_0003(empty_database_url: str, tmp_path: Path) -> None:
    migrations = Path(__file__).resolve().parents[2] / "db" / "migrations"
    for name in ("0001_initial.sql", "0002_immutable_observations.sql"):
        (tmp_path / name).write_bytes((migrations / name).read_bytes())

    first = migrate(empty_database_url, migrations_dir=tmp_path)
    assert first == ["0001", "0002"]

    with psycopg.connect(
        empty_database_url, cursor_factory=psycopg.ClientCursor, autocommit=True
    ) as conn:
        conn.execute(
            """
            insert into companies (id, slug, name, website)
            values (
              'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
              'from0002',
              'From 0002 Co',
              'https://from0002.example.test'
            )
            """
        )
        conn.execute(
            """
            insert into policy_sources (id, company_id, url, health_status)
            values (
              'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
              'https://from0002.example.test/privacy',
              'healthy'
            )
            """
        )
        conn.execute(
            """
            insert into snapshots (
              id, source_id, http_status, markdown, doc_hash, is_valid
            )
            values (
              'cccccccc-cccc-cccc-cccc-cccccccccccc',
              'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              200,
              E'# Privacy\\nWe collect your email address to create an account.',
              'from0002hash',
              true
            )
            """
        )
        conn.execute(
            """
            update policy_sources
            set current_snapshot_id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
            where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
            """
        )
        observation_count = conn.execute("select count(*) from observations").fetchone()
        assert observation_count is not None
        before_observations = observation_count[0]

    second = migrate(empty_database_url)
    assert second == ["0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010", "0011"]
    with psycopg.connect(empty_database_url, row_factory=dict_row) as conn:
        source = conn.execute(
            """
            select current_snapshot_id, due_at, retry_count, quarantine_reason
            from policy_sources
            where id = %s
            """,
            ("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",),
        ).fetchone()
        after = conn.execute("select count(*) as n from observations").fetchone()
        jobs = conn.execute("select count(*) as n from fetch_jobs").fetchone()
        actions = conn.execute("select count(*) as n from source_operator_actions").fetchone()
    assert source is not None
    assert str(source["current_snapshot_id"]) == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert source["due_at"] is not None
    assert source["retry_count"] == 0
    assert source["quarantine_reason"] is None
    assert after is not None and after["n"] == before_observations
    assert jobs is not None and jobs["n"] == 0
    assert actions is not None and actions["n"] == 0
    assert [row[0] for row in _ledger(empty_database_url)] == HEAD_VERSIONS


def test_migrate_rejects_ledger_version_missing_from_directory(
    empty_database_url: str, tmp_path: Path
) -> None:
    migrate(empty_database_url)
    with pytest.raises(MigrationError, match="missing from migrations directory"):
        migrate(empty_database_url, migrations_dir=tmp_path)


def test_concurrent_migrate_serializes_on_advisory_lock(empty_database_url: str) -> None:
    def run(_index: int) -> list[str]:
        return migrate(empty_database_url)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))

    applied = [item for batch in results for item in batch]
    assert sorted(applied) == HEAD_VERSIONS
    assert [row[0] for row in _ledger(empty_database_url)] == HEAD_VERSIONS
