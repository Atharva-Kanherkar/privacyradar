"""Forward-only numbered SQL migrations with a checksum ledger."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
DOCKER_MIGRATIONS_DIR = Path("/app/db/migrations")
FILENAME_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


def default_migrations_dir() -> Path:
    override = os.environ.get("PRIVACYRADAR_MIGRATIONS_DIR")
    if override:
        return Path(override)
    if DEFAULT_MIGRATIONS_DIR.is_dir():
        return DEFAULT_MIGRATIONS_DIR
    if DOCKER_MIGRATIONS_DIR.is_dir():
        return DOCKER_MIGRATIONS_DIR
    return DEFAULT_MIGRATIONS_DIR


LEDGER_SQL = """
create table if not exists schema_migrations (
  version     text primary key,
  name        text not null,
  checksum    text not null,
  applied_at  timestamptz not null default now(),
  execution_ms integer not null default 0
)
"""
# Stable advisory-lock key for PrivacyRadar migrations.
LOCK_KEY = 0x5052_4D49  # 'PRMI'


class MigrationError(RuntimeError):
    """Raised when migrations cannot be applied safely."""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    sql_bytes: bytes

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql_bytes).hexdigest()

    @property
    def sql(self) -> str:
        return self.sql_bytes.decode("utf-8")


def discover_migrations(directory: Path | None = None) -> list[Migration]:
    migrations_dir = directory or DEFAULT_MIGRATIONS_DIR
    if not migrations_dir.is_dir():
        raise MigrationError(f"migrations directory does not exist: {migrations_dir}")

    found: list[Migration] = []
    versions: set[str] = set()
    for path in sorted(migrations_dir.iterdir()):
        if not path.is_file():
            continue
        match = FILENAME_RE.match(path.name)
        if match is None:
            continue
        version, name = match.group(1), match.group(2)
        if version in versions:
            raise MigrationError(f"duplicate migration version {version}")
        versions.add(version)
        found.append(
            Migration(
                version=version,
                name=name,
                path=path,
                sql_bytes=path.read_bytes(),
            )
        )
    found.sort(key=lambda item: item.version)
    return found


def _connect(database_url: str) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        cursor_factory=psycopg.ClientCursor,
    )


def _ensure_ledger(conn: psycopg.Connection[dict[str, Any]]) -> None:
    conn.execute(LEDGER_SQL)


def _applied_rows(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "select version, name, checksum, applied_at, execution_ms from schema_migrations"
    ).fetchall()
    return {row["version"]: row for row in rows}


def migrate(
    database_url: str,
    migrations_dir: Path | None = None,
) -> list[str]:
    """Apply pending migrations. Returns versions applied in this invocation."""
    migrations = discover_migrations(migrations_dir or default_migrations_dir())
    discovered = {item.version: item for item in migrations}
    applied_now: list[str] = []
    with _connect(database_url) as conn:
        conn.autocommit = True
        conn.execute("select pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
            _ensure_ledger(conn)
            recorded = _applied_rows(conn)
            missing_files = sorted(set(recorded) - set(discovered))
            if missing_files:
                raise MigrationError(
                    "ledger has versions missing from migrations directory: "
                    + ", ".join(missing_files)
                )
            for migration in migrations:
                existing = recorded.get(migration.version)
                if existing is not None:
                    if existing["checksum"] != migration.checksum:
                        raise MigrationError(
                            f"checksum mismatch for migration {migration.version} "
                            f"({migration.name}): ledger={existing['checksum']} "
                            f"file={migration.checksum}"
                        )
                    continue
                started = time.perf_counter()
                conn.autocommit = False
                try:
                    conn.execute(migration.sql)
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    conn.execute(
                        """
                        insert into schema_migrations (version, name, checksum, execution_ms)
                        values (%s, %s, %s, %s)
                        """,
                        (
                            migration.version,
                            migration.name,
                            migration.checksum,
                            elapsed_ms,
                        ),
                    )
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    raise MigrationError(
                        f"migration {migration.version}_{migration.name} failed: {exc}"
                    ) from exc
                finally:
                    conn.autocommit = True
                recorded[migration.version] = {
                    "version": migration.version,
                    "checksum": migration.checksum,
                }
                applied_now.append(migration.version)
                logger.info(
                    "applied migration %s_%s in %sms",
                    migration.version,
                    migration.name,
                    int((time.perf_counter() - started) * 1000),
                )
        finally:
            conn.autocommit = True
            conn.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
    return applied_now
