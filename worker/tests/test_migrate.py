from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest

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
}


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
    assert applied == ["0001", "0002"]
    assert _tables(empty_database_url) >= REQUIRED_TABLES
    ledger = _ledger(empty_database_url)
    assert [row[0] for row in ledger] == ["0001", "0002"]


def test_migrate_is_idempotent(empty_database_url: str) -> None:
    first = migrate(empty_database_url)
    tables_after_first = _tables(empty_database_url)
    ledger_after_first = _ledger(empty_database_url)
    second = migrate(empty_database_url)
    assert first == ["0001", "0002"]
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
    assert _ledger(empty_database_url) == [
        ("0001", discover_migrations(tmp_path)[0].checksum)
    ]


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
    assert applied == ["0001", "0002"]
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
    assert [row[0] for row in _ledger(empty_database_url)] == ["0001", "0002"]


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
    with psycopg.connect(empty_database_url, row_factory=None) as conn:
        valid = conn.execute(
            "select is_valid, id from snapshots order by fetched_at"
        ).fetchall()
        current = conn.execute(
            "select current_snapshot_id, health_status from policy_sources"
        ).fetchone()
        attempts = conn.execute(
            "select status, error_code from source_attempts order by status desc"
        ).fetchall()
        observations = conn.execute("select count(*) from observations").fetchone()
    valid_map = {str(row[1]): row[0] for row in valid}
    assert valid_map["cccccccc-cccc-cccc-cccc-cccccccccccc"] is True
    assert valid_map["dddddddd-dddd-dddd-dddd-dddddddddddd"] is False
    assert current is not None
    assert str(current[0]) == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert current[1] == "healthy"
    assert observations is not None and observations[0] == 1
    statuses = {row[0] for row in attempts}
    assert "succeeded" in statuses
    assert "failed" in statuses
    failed_codes = {row[1] for row in attempts if row[0] == "failed"}
    assert failed_codes <= {"timeout", "empty", "network"}
    assert "timeout" in failed_codes or "empty" in failed_codes


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
    assert applied == ["0001", "0002"]
    assert [row[0] for row in _ledger(empty_database_url)] == ["0001", "0002"]
