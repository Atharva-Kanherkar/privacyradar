"""Persistence helpers for deterministic fixtures."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid5

import psycopg
from psycopg.types.json import Json

from privacyradar.hashing import NORMALIZER_VERSION
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
    if observation.fetch_error is not None:
        raise FixturePersistenceUnsupported(
            "failed fetches persist as source_attempts, not observations"
        )
    raw = observation.raw_html.encode("utf-8")
    raw_digest = hashlib.sha256(raw).hexdigest()
    conn.execute(
        """
        insert into snapshots (
          id, source_id, fetched_at, http_status, content_type, raw_html, markdown,
          doc_hash, section_hashes, fetch_error, final_url, region, strategy,
          byte_count, raw_sha256, normalized_sha256, normalizer_version, is_valid
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, null, %s, %s, 'http', %s, %s, %s, %s, true)
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
            observation.resolved_url,
            observation.region,
            len(raw),
            raw_digest,
            observation.doc_hash,
            NORMALIZER_VERSION,
        ),
    )
    attempt_id = str(uuid5(observation.id, "attempt"))
    conn.execute(
        """
        insert into source_attempts (
          id, source_id, started_at, finished_at, strategy, status,
          http_status, content_type, request_url, resolved_url,
          snapshot_id, byte_count, normalizer_version
        )
        values (%s, %s, %s, %s, 'http', 'succeeded', %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            attempt_id,
            str(observation.source_id),
            observation.fetched_at,
            observation.fetched_at,
            observation.http_status,
            observation.content_type,
            observation.resolved_url,
            observation.resolved_url,
            str(observation.id),
            len(raw),
            NORMALIZER_VERSION,
        ),
    )
    conn.execute(
        """
        insert into observations (
          id, source_id, snapshot_id, attempt_id, observed_at, region,
          previous_snapshot_id
        )
        values (%s, %s, %s, %s, %s, %s, null)
        """,
        (
            str(observation.id),
            str(observation.source_id),
            str(observation.id),
            attempt_id,
            observation.fetched_at,
            observation.region,
        ),
    )
    conn.execute(
        """
        update source_attempts
        set observation_id = %s
        where id = %s
        """,
        (str(observation.id), attempt_id),
    )
    conn.execute(
        """
        update policy_sources
        set current_snapshot_id = %s,
            current_observation_id = %s,
            health_status = 'healthy',
            last_attempt_at = %s,
            last_success_at = %s,
            consecutive_failures = 0,
            last_failure_code = null
        where id = %s
        """,
        (
            str(observation.id),
            str(observation.id),
            observation.fetched_at,
            observation.fetched_at,
            str(observation.source_id),
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
    conn.execute(
        """
        insert into change_events (
          company_id, source_id, from_snapshot, to_snapshot,
          materiality, headline, summary, publication_state
        )
        values (%s, %s, %s, %s, 'material', 'UNPUBLISHED_FIXTURE_HEADLINE',
                'Held for review.', 'review_pending')
        """,
        (str(company.id), str(source.id), str(observation.id), str(observation.id)),
    )
    return 1
