"""Persistence helpers for deterministic fixtures."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid5

import psycopg
from psycopg.types.json import Json

from privacyradar.hashing import NORMALIZER_VERSION
from privacyradar.taxonomy import PROMPT_VERSION, TAXONOMY_VERSION, claim_key
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
    stable_uuid,
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
    conn: psycopg.Connection[dict[str, Any]], user: UserFixture
) -> None:
    conn.execute(
        """
        insert into auth_users (id, name, email, email_verified, created_at, updated_at)
        values (%s, %s, %s, true, %s, %s)
        """,
        (
            str(user.id),
            user.handle,
            user.email,
            user.created_at,
            user.created_at,
        ),
    )
    conn.execute(
        """
        insert into consumer_profiles (user_id, region, created_at, updated_at)
        values (%s, %s, %s, %s)
        """,
        (str(user.id), user.region, user.created_at, user.created_at),
    )
    conn.execute(
        """
        insert into consent_events (user_id, action)
        values (%s, 'signup')
        """,
        (str(user.id),),
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
    created = 0
    if existing is None:
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
              id, company_id, source_id, from_snapshot, to_snapshot,
              materiality, headline, summary, publication_state
            )
            values (%s, %s, %s, %s, %s, 'material', 'UNPUBLISHED_FIXTURE_HEADLINE',
                    'Held for review.', 'review_pending')
            """,
            (
                str(stable_uuid("unpublished-event", company.slug)),
                str(company.id),
                str(source.id),
                str(observation.id),
                str(observation.id),
            ),
        )
        created = 1
    _ensure_published_fixture(conn, company)
    return created


def _ensure_published_fixture(
    conn: psycopg.Connection[dict[str, Any]], company: CompanyFixture
) -> None:
    already = conn.execute(
        "select 1 from publication_revisions where company_id = %s limit 1",
        (str(company.id),),
    ).fetchone()
    if already is not None:
        return
    ctx = conn.execute(
        """
        select s.id as source_id, o.id as observation_id, o.snapshot_id, snap.markdown
        from policy_sources s
        join observations o on o.source_id = s.id
        join snapshots snap on snap.id = o.snapshot_id
        where s.company_id = %s
        limit 1
        """,
        (str(company.id),),
    ).fetchone()
    if ctx is None:
        return
    markdown = str(ctx["markdown"] or "")
    quote = "We collect your email address to create an account."
    start = markdown.find(quote)
    if start < 0:
        return
    run_id = str(stable_uuid("fixture-run", company.slug))
    claim_id = str(stable_uuid("fixture-claim", company.slug))
    revision_id = str(stable_uuid("fixture-revision", company.slug))
    event_id = str(stable_uuid("published-event", company.slug))
    key = claim_key(
        taxonomy_version=TAXONOMY_VERSION,
        category="data_collected",
        attribute="email",
        polarity="disclosed",
    )
    conn.execute(
        """
        insert into extraction_runs (
          id, observation_id, snapshot_id, taxonomy_version, prompt_version,
          model, status
        )
        values (%s, %s, %s, %s, %s, 'fixture', 'succeeded')
        """,
        (
            run_id,
            str(ctx["observation_id"]),
            str(ctx["snapshot_id"]),
            TAXONOMY_VERSION,
            PROMPT_VERSION,
        ),
    )
    conn.execute(
        """
        insert into candidate_claims (
          id, run_id, claim_key, category, attribute, polarity,
          confidence, validation_state
        )
        values (%s, %s, %s, 'data_collected', 'email', 'disclosed', 1, 'valid')
        """,
        (claim_id, run_id, key),
    )
    conn.execute(
        """
        insert into evidence_spans (
          id, claim_id, snapshot_id, quote, section, start_offset, end_offset,
          validation_result
        )
        values (%s, %s, %s, %s, 'Privacy', %s, %s, 'exact')
        """,
        (
            str(stable_uuid("fixture-span", company.slug)),
            claim_id,
            str(ctx["snapshot_id"]),
            quote,
            start,
            start + len(quote),
        ),
    )
    conn.execute(
        """
        insert into change_events (
          id, company_id, source_id, from_snapshot, to_snapshot,
          materiality, headline, summary, quotes, publication_state, published_at
        )
        values (
          %s, %s, %s, %s, %s, 'material', 'PUBLISHED_FIXTURE_HEADLINE',
          'Email collection language.', %s, 'published', now()
        )
        on conflict (id) do nothing
        """,
        (
            event_id,
            str(company.id),
            str(ctx["source_id"]),
            str(ctx["snapshot_id"]),
            str(ctx["snapshot_id"]),
            Json([{"text": quote, "section": "Privacy"}]),
        ),
    )
    conn.execute(
        """
        insert into publication_revisions (
          id, company_id, observation_id, extraction_run_id, change_event_id,
          revision_n, state, actor
        )
        values (%s, %s, %s, %s, %s, 1, 'published', 'cli:local')
        """,
        (
            revision_id,
            str(company.id),
            str(ctx["observation_id"]),
            run_id,
            event_id,
        ),
    )
    conn.execute(
        """
        insert into published_claims (
          id, revision_id, candidate_claim_id, claim_key, category, attribute,
          polarity, quote, snapshot_id, start_offset, end_offset
        )
        values (%s, %s, %s, %s, 'data_collected', 'email', 'disclosed', %s, %s, %s, %s)
        """,
        (
            str(stable_uuid("fixture-published-claim", company.slug)),
            revision_id,
            claim_id,
            key,
            quote,
            str(ctx["snapshot_id"]),
            start,
            start + len(quote),
        ),
    )
