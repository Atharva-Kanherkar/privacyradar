from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from privacyradar.migrate import (
    DEFAULT_MIGRATIONS_DIR,
    MigrationError,
    discover_migrations,
)


def test_parse_migrations_orders_numeric_versions(tmp_path: Path) -> None:
    (tmp_path / "0002_later.sql").write_text("select 2;\n")
    (tmp_path / "0001_first.sql").write_text("select 1;\n")
    (tmp_path / "readme.txt").write_text("ignored")
    (tmp_path / "notes.sql").write_text("ignored")

    found = discover_migrations(tmp_path)

    assert [item.version for item in found] == ["0001", "0002"]
    assert found[0].name == "first"
    assert found[1].name == "later"


def test_migration_checksum_is_sha256_of_bytes(tmp_path: Path) -> None:
    path = tmp_path / "0001_example.sql"
    payload = b"select 1;\n"
    path.write_bytes(payload)

    found = discover_migrations(tmp_path)

    assert found[0].checksum == hashlib.sha256(payload).hexdigest()
    path.write_bytes(b"select 2;\n")
    changed = discover_migrations(tmp_path)
    assert changed[0].checksum != found[0].checksum


def test_discover_migrations_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(MigrationError, match="does not exist"):
        discover_migrations(tmp_path / "missing")


def test_discover_migrations_skips_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "0001_first.sql").write_text("select 1;\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "0002_nope.sql").write_text("select 2;\n")

    found = discover_migrations(tmp_path)

    assert [item.version for item in found] == ["0001"]


def test_discover_migrations_rejects_duplicate_versions(tmp_path: Path) -> None:
    (tmp_path / "0001_one.sql").write_text("select 1;\n")
    (tmp_path / "0001_two.sql").write_text("select 2;\n")

    with pytest.raises(MigrationError, match="duplicate migration version"):
        discover_migrations(tmp_path)


def test_default_migrations_include_initial_and_observations() -> None:
    found = discover_migrations(DEFAULT_MIGRATIONS_DIR)
    assert [item.version for item in found] == ["0001", "0002"]
    assert found[0].name == "initial"
    assert found[1].name == "immutable_observations"


def test_schema_sql_is_current_head_reference() -> None:
    reference = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
    body = reference.read_text()
    initial = (DEFAULT_MIGRATIONS_DIR / "0001_initial.sql").read_text()
    assert "create table if not exists companies" in body
    assert "create table if not exists snapshots" in initial
    assert "create table if not exists source_attempts" in body
    assert "create table if not exists observations" in body
    assert "create table if not exists document_changes" in body
    assert "schema_migrations" not in body
