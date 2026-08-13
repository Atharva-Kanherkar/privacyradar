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
    assert applied == ["0001"]
    assert _tables(empty_database_url) >= REQUIRED_TABLES
    ledger = _ledger(empty_database_url)
    assert len(ledger) == 1
    assert ledger[0][0] == "0001"
    assert ledger[0][1] == discover_migrations()[0].checksum


def test_migrate_is_idempotent(empty_database_url: str) -> None:
    first = migrate(empty_database_url)
    tables_after_first = _tables(empty_database_url)
    ledger_after_first = _ledger(empty_database_url)
    second = migrate(empty_database_url)
    assert first == ["0001"]
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
              '# Privacy\\nWe collect email.',
              'abc123',
              '{}'::jsonb
            )
            """
        )

    applied = migrate(empty_database_url)
    assert applied == ["0001"]
    with psycopg.connect(empty_database_url) as conn:
        company = conn.execute(
            "select slug, name from companies where id = %s",
            ("11111111-1111-1111-1111-111111111111",),
        ).fetchone()
        snapshot = conn.execute(
            "select doc_hash from snapshots where id = %s",
            ("33333333-3333-3333-3333-333333333333",),
        ).fetchone()
        assert company is not None
        assert company[0] == "prototype"
        assert snapshot is not None
        assert snapshot[0] == "abc123"
    assert _ledger(empty_database_url)[0][0] == "0001"


def test_concurrent_migrate_serializes_on_advisory_lock(empty_database_url: str) -> None:
    def run(_index: int) -> list[str]:
        return migrate(empty_database_url)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))

    applied = [item for batch in results for item in batch]
    assert applied == ["0001"]
    assert _ledger(empty_database_url) == [
        ("0001", discover_migrations()[0].checksum)
    ]
