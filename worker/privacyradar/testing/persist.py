"""Persistence helpers for deterministic fixtures."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Json

from privacyradar.testing.fixtures import (
    ClaimFixture,
    CompanyFixture,
    FollowFixture,
    NotificationFixture,
    ObservationFixture,
    SourceFixture,
    UserFixture,
    make_claim,
    make_company,
    make_observation,
    make_source,
)


class FixturePersistenceUnsupported(RuntimeError):
    """The target table does not exist yet; later issues own that schema."""


def persist_company(
    conn: psycopg.Connection[dict[str, Any]], company: CompanyFixture
) -> None:
    conn.execute(
        """
        insert into companies (id, slug, name, website, category, created_at)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (
            str(company.id),
            company.slug,
            company.name,
            company.website,
            company.category,
            company.created_at,
        ),
    )


def persist_source(
    conn: psycopg.Connection[dict[str, Any]], source: SourceFixture
) -> None:
    conn.execute(
        """
        insert into policy_sources (
          id, company_id, kind, url, region, enabled, crawl_delay_s
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(source.id),
            str(source.company_id),
            source.kind,
            source.url,
            source.region,
            source.enabled,
            source.crawl_delay_s,
        ),
    )


def persist_observation(
    conn: psycopg.Connection[dict[str, Any]], observation: ObservationFixture
) -> None:
    conn.execute(
        """
        insert into snapshots (
          id, source_id, fetched_at, http_status, content_type, raw_html, markdown,
          doc_hash, section_hashes, fetch_error
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(observation.id),
            str(observation.source_id),
            observation.fetched_at,
            observation.http_status,
            observation.content_type,
            observation.raw_html,
            observation.markdown,
            observation.doc_hash,
            Json(observation.section_hashes),
            observation.fetch_error,
        ),
    )


def persist_claim(
    conn: psycopg.Connection[dict[str, Any]], claim: ClaimFixture
) -> None:
    conn.execute(
        """
        insert into extractions (id, snapshot_id, model, practices, created_at)
        values (%s, %s, %s, %s, %s)
        """,
        (
            str(claim.id),
            str(claim.observation_id),
            claim.model,
            Json(claim.practices),
            claim.created_at,
        ),
    )


def persist_user(
    _conn: psycopg.Connection[dict[str, Any]], user: UserFixture
) -> None:
    raise FixturePersistenceUnsupported(
        f"users table is owned by issue #10; cannot persist {user.handle}"
    )


def persist_follow(
    _conn: psycopg.Connection[dict[str, Any]], follow: FollowFixture
) -> None:
    raise FixturePersistenceUnsupported(
        f"watches table is owned by issue #11; cannot persist follow {follow.id}"
    )


def persist_notification(
    _conn: psycopg.Connection[dict[str, Any]], notification: NotificationFixture
) -> None:
    raise FixturePersistenceUnsupported(
        f"notification tables are owned by issue #12; cannot persist {notification.id}"
    )


def seed_public_fixtures(conn: psycopg.Connection[dict[str, Any]]) -> int:
    """Insert the default public smoke company if it is not already present."""
    company = make_company()
    existing = conn.execute(
        "select 1 from companies where slug = %s", (company.slug,)
    ).fetchone()
    if existing is not None:
        return 0
    source = make_source(company)
    observation = make_observation(source)
    claim = make_claim(observation, company)
    persist_company(conn, company)
    persist_source(conn, source)
    persist_observation(conn, observation)
    persist_claim(conn, claim)
    return 1
