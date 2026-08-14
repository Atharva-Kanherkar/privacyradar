from __future__ import annotations

import getpass
import os
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest

from privacyradar.migrate import migrate


def _default_admin_url() -> str:
    user = getpass.getuser()
    return f"postgresql://{user}@localhost:5432/postgres"


def _with_database(url: str, database: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _can_connect(url: str) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("select 1")
        return True
    except psycopg.Error:
        return False


@pytest.fixture(scope="session")
def postgres_admin_url() -> str:
    configured = os.environ.get("TEST_ADMIN_DATABASE_URL") or os.environ.get(
        "TEST_DATABASE_URL"
    )
    if configured:
        parsed = urlparse(configured)
        dbname = (parsed.path or "/").lstrip("/") or "postgres"
        if dbname != "postgres":
            admin = _with_database(configured, "postgres")
            if _can_connect(admin):
                return admin
            if _can_connect(configured):
                return configured
        elif _can_connect(configured):
            return configured
    admin = _default_admin_url()
    if _can_connect(admin):
        return admin
    if os.environ.get("CI"):
        pytest.fail("PostgreSQL is required in CI for worker tests")
    pytest.skip("PostgreSQL is not available")


@pytest.fixture
def empty_database_url(postgres_admin_url: str) -> Iterator[str]:
    """Create an isolated database and drop it after the test."""
    parsed = urlparse(postgres_admin_url)
    current_db = (parsed.path or "/postgres").lstrip("/") or "postgres"
    if os.environ.get("TEST_DATABASE_URL") and current_db != "postgres":
        # CI service databases often cannot CREATE DATABASE. Truncate/drop
        # objects instead by using a unique schema? We still try CREATE first.
        pass

    name = f"privacyradar_test_{uuid.uuid4().hex[:12]}"
    url = _with_database(postgres_admin_url, name)
    try:
        with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
            conn.execute(f'create database "{name}"')
    except psycopg.Error as exc:
        if os.environ.get("CI"):
            pytest.fail(f"could not create ephemeral test database: {exc}")
        pytest.skip(f"could not create ephemeral test database: {exc}")
    try:
        yield url
    finally:
        with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
            conn.execute(
                """
                select pg_terminate_backend(pid)
                from pg_stat_activity
                where datname = %s and pid <> pg_backend_pid()
                """,
                (name,),
            )
            conn.execute(f'drop database if exists "{name}"')


@pytest.fixture(scope="session")
def migrated_database_url(postgres_admin_url: str) -> Iterator[str]:
    name = f"privacyradar_it_{uuid.uuid4().hex[:12]}"
    url = _with_database(postgres_admin_url, name)
    try:
        with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
            conn.execute(f'create database "{name}"')
    except psycopg.Error as exc:
        if os.environ.get("CI"):
            pytest.fail(f"could not create integration database: {exc}")
        pytest.skip(f"could not create integration database: {exc}")
    migrate(url)
    try:
        yield url
    finally:
        with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
            conn.execute(
                """
                select pg_terminate_backend(pid)
                from pg_stat_activity
                where datname = %s and pid <> pg_backend_pid()
                """,
                (name,),
            )
            conn.execute(f'drop database if exists "{name}"')


@pytest.fixture
def db_url(migrated_database_url: str) -> str:
    with psycopg.connect(migrated_database_url, autocommit=True) as conn:
        conn.execute(
            """
            truncate
              evidence_spans,
              candidate_claims,
              extraction_runs,
              source_operator_actions,
              fetch_jobs,
              document_changes,
              observations,
              source_attempts,
              change_events,
              extractions,
              snapshots,
              policy_sources,
              companies
            restart identity cascade
            """
        )
    return migrated_database_url


@pytest.fixture(scope="session")
def redis_url() -> str:
    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as redis_lib
    except ImportError:
        if os.environ.get("CI"):
            pytest.fail("redis-py is required in CI")
        pytest.skip("redis-py is not installed")
    try:
        client = redis_lib.Redis.from_url(url, socket_connect_timeout=1)
        assert client.ping() is True
    except Exception as exc:
        if os.environ.get("CI"):
            pytest.fail(f"Redis is required in CI: {exc}")
        pytest.skip(f"Redis is not available: {exc}")
    return url
