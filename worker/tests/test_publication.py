from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.claims import CandidateClaim, EvidenceQuote
from privacyradar.extract import extract_observation
from privacyradar.publication import (
    PublicationError,
    publish_run,
    publish_stats,
    reject_event,
    resolve_correction,
    rollback_revision,
    set_publication_enabled,
    submit_correction,
    validate_claim_for_publication,
)
from privacyradar.testing.fixtures import make_company, make_observation, make_source
from privacyradar.testing.persist import persist_company, persist_observation, persist_source

pytestmark = pytest.mark.integration

POLICY = "# Privacy\nWe collect your email address to create an account.\n"
QUOTE = "We collect your email address to create an account."


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


class FixedExtractor:
    def extract(
        self,
        *,
        instructions: str,
        document: str,
        taxonomy_version: str,
        model: str,
    ) -> list[CandidateClaim]:
        del instructions, document, taxonomy_version, model
        return [
            CandidateClaim(
                category="data_collected",
                attribute="email",
                polarity="disclosed",
                quotes=[EvidenceQuote(text=QUOTE, section="Privacy")],
                confidence=1.0,
            )
        ]


def _seed_run(db_url: str, slug: str = "pub-co") -> tuple[str, str, str]:
    company = make_company(slug=slug)
    source = make_source(company)
    observation = make_observation(source, markdown=POLICY)
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        persist_observation(conn, observation)
        outcome = extract_observation(conn, str(observation.id), FixedExtractor())
        conn.commit()
    assert outcome is not None
    return str(company.id), str(observation.id), outcome.run_id


def test_invalid_actor_rejected(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="actor-co")
    with _connect(db_url) as conn, pytest.raises(PublicationError, match="invalid_actor"):
        publish_run(conn, run_id, actor="not an email@x.test")


def test_publication_switch_off_refuses_publish(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="switch-co")
    with _connect(db_url) as conn:
        set_publication_enabled(conn, False)
        with pytest.raises(PublicationError, match="publication_disabled"):
            publish_run(conn, run_id, actor="cli:local")
        set_publication_enabled(conn, True)


def test_quote_missing_cannot_publish(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="quote-co")
    with _connect(db_url) as conn:
        snap = conn.execute(
            "select snapshot_id from extraction_runs where id = %s", (run_id,)
        ).fetchone()
        assert snap is not None
        bad_id = str(uuid4())
        conn.execute(
            """
            insert into candidate_claims (
              id, run_id, claim_key, category, attribute, polarity,
              confidence, validation_state
            )
            values (%s, %s, 'badkey', 'data_collected', 'email', 'disclosed', 1, 'valid')
            """,
            (bad_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (%s, %s, %s, 'not in the snapshot', 'missing')
            """,
            (str(uuid4()), bad_id, str(snap["snapshot_id"])),
        )
        assert validate_claim_for_publication(conn, bad_id) == "quote_missing"
        with pytest.raises(PublicationError, match="quote_missing"):
            publish_run(conn, run_id, actor="cli:local")
        conn.rollback()
        n = conn.execute("select count(*) as n from publication_revisions").fetchone()
        assert n is not None and n["n"] == 0


def test_offset_mismatch_cannot_publish(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="offset-co")
    with _connect(db_url) as conn:
        snap = conn.execute(
            "select snapshot_id from extraction_runs where id = %s", (run_id,)
        ).fetchone()
        assert snap is not None
        bad_id = str(uuid4())
        conn.execute(
            """
            insert into candidate_claims (
              id, run_id, claim_key, category, attribute, polarity,
              confidence, validation_state
            )
            values (%s, %s, 'offkey', 'data_collected', 'email', 'disclosed', 1, 'valid')
            """,
            (bad_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, start_offset, end_offset, validation_result
            )
            values (%s, %s, %s, %s, 0, 1, 'exact')
            """,
            (str(uuid4()), bad_id, str(snap["snapshot_id"]), QUOTE),
        )
        assert validate_claim_for_publication(conn, bad_id) == "offset_mismatch"


def test_unsupported_claim_cannot_publish(db_url: str) -> None:
    company = make_company(slug="unsup-co")
    source = make_source(company)
    observation = make_observation(source, markdown=POLICY)

    class BadExtractor:
        def extract(self, **kwargs: object) -> list[CandidateClaim]:
            del kwargs
            return [
                CandidateClaim(
                    category="data_collected",
                    attribute="email",
                    polarity="disclosed",
                    quotes=[EvidenceQuote(text="We harvest DNA in secret.")],
                    confidence=1.0,
                )
            ]

    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        persist_observation(conn, observation)
        outcome = extract_observation(conn, str(observation.id), BadExtractor())
        conn.commit()
        assert outcome is not None
        with pytest.raises(PublicationError, match="no_valid_claims"):
            publish_run(conn, outcome.run_id, actor="cli:local")


def test_malformed_model_output_cannot_publish(db_url: str) -> None:
    company = make_company(slug="malform-co")
    source = make_source(company)
    observation = make_observation(source, markdown=POLICY)

    class JunkExtractor:
        def extract(self, **kwargs: object) -> list[CandidateClaim]:
            del kwargs
            return [
                CandidateClaim(
                    category="not_a_category",
                    attribute="nope",
                    polarity="disclosed",
                    quotes=[EvidenceQuote(text=QUOTE)],
                    confidence=1.0,
                )
            ]

    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        persist_observation(conn, observation)
        outcome = extract_observation(conn, str(observation.id), JunkExtractor())
        conn.commit()
        assert outcome is not None
        with pytest.raises(PublicationError, match="no_valid_claims"):
            publish_run(conn, outcome.run_id, actor="cli:local")


def test_publish_run_is_atomic(db_url: str) -> None:
    test_quote_missing_cannot_publish(db_url)


def test_snapshot_mismatch_cannot_publish(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="snap-co")
    with _connect(db_url) as conn:
        other = str(uuid4())
        source = conn.execute("select id from policy_sources limit 1").fetchone()
        assert source is not None
        conn.execute(
            """
            insert into snapshots (id, source_id, doc_hash, markdown, is_valid)
            values (%s, %s, 'other', %s, true)
            """,
            (other, str(source["id"]), POLICY),
        )
        bad_id = str(uuid4())
        conn.execute(
            """
            insert into candidate_claims (
              id, run_id, claim_key, category, attribute, polarity,
              confidence, validation_state
            )
            values (%s, %s, 'snapkey', 'data_collected', 'email', 'disclosed', 1, 'valid')
            """,
            (bad_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (%s, %s, %s, %s, 'exact')
            """,
            (str(uuid4()), bad_id, other, QUOTE),
        )
        assert validate_claim_for_publication(conn, bad_id) == "snapshot_mismatch"


def test_forbidden_publication_transition(db_url: str) -> None:
    company_id, observation_id, run_id = _seed_run(db_url, slug="trans-co")
    with _connect(db_url) as conn:
        source = conn.execute(
            "select id from policy_sources where company_id = %s", (company_id,)
        ).fetchone()
        snap = conn.execute(
            "select snapshot_id from observations where id = %s", (observation_id,)
        ).fetchone()
        assert source is not None and snap is not None
        event = conn.execute(
            """
            insert into change_events (
              company_id, source_id, from_snapshot, to_snapshot,
              materiality, headline, summary, publication_state
            )
            values (%s, %s, %s, %s, 'material', 'h', 's', 'rejected')
            returning id
            """,
            (company_id, str(source["id"]), str(snap["snapshot_id"]), str(snap["snapshot_id"])),
        ).fetchone()
        assert event is not None
        with pytest.raises(PublicationError, match="forbidden_transition"):
            reject_event(conn, str(event["id"]), actor="cli:local", reason="duplicate")


def test_cosmetic_event_is_rejected_not_listed(db_url: str) -> None:
    from privacyradar.db import insert_change_event

    company_id, observation_id, _run_id = _seed_run(db_url, slug="cosmetic-co")
    with _connect(db_url) as conn:
        source = conn.execute(
            "select id from policy_sources where company_id = %s", (company_id,)
        ).fetchone()
        snap = conn.execute(
            "select snapshot_id from observations where id = %s", (observation_id,)
        ).fetchone()
        assert source is not None and snap is not None
        insert_change_event(
            conn,
            company_id=company_id,
            source_id=str(source["id"]),
            from_snapshot=str(snap["snapshot_id"]),
            to_snapshot=str(snap["snapshot_id"]),
            materiality="cosmetic",
            headline="Date stamp",
            summary="footer",
            data_types_added=[],
            data_types_removed=[],
            quotes=[],
        )
        row = conn.execute(
            "select publication_state from change_events where headline = 'Date stamp'"
        ).fetchone()
        listed = conn.execute(
            """
            select count(*) as n from change_events
            where publication_state in ('published', 'corrected')
            """
        ).fetchone()
        assert row is not None and row["publication_state"] == "rejected"
        assert listed is not None and listed["n"] == 0


def test_review_actions_are_append_only(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="audit-co")
    with _connect(db_url) as conn:
        published = publish_run(conn, run_id, actor="cli:local")
        conn.commit()
        action = conn.execute("select id from review_actions limit 1").fetchone()
        assert action is not None
        with pytest.raises(psycopg.Error):
            conn.execute("delete from review_actions where id = %s", (str(action["id"]),))
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute(
                "update publication_revisions set actor = 'tamper' where id = %s",
                (published.revision_id,),
            )


def test_rollback_preserves_prior_revision_row(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="roll-co")
    with _connect(db_url) as conn:
        first = publish_run(conn, run_id, actor="cli:local")
        second = publish_run(conn, run_id, actor="cli:local")
        conn.commit()
        rollback_revision(conn, second.revision_id, actor="cli:local", reason="bad_rev")
        conn.commit()
        rows = conn.execute(
            "select id, state from publication_revisions order by revision_n"
        ).fetchall()
        ids = [str(row["id"]) for row in rows]
        assert first.revision_id in ids
        assert second.revision_id in ids
        assert any(row["state"] == "rolled_back" for row in rows)
        assert any(row["state"] == "published" for row in rows)


def test_correction_creates_replacement_revision(db_url: str) -> None:
    company_id, _, run_id = _seed_run(db_url, slug="corr-co")
    with _connect(db_url) as conn:
        published = publish_run(conn, run_id, actor="cli:local")
        correction_id = submit_correction(
            conn,
            company_id=company_id,
            revision_id=published.revision_id,
            note="Wrong polarity.",
            actor="cli:local",
        )
        replacement = resolve_correction(
            conn,
            correction_id,
            actor="cli:local",
            decision="corrected",
            note="Republished from the same run.",
        )
        conn.commit()
        row = conn.execute(
            "select state, replacement_revision_id from corrections where id = %s",
            (correction_id,),
        ).fetchone()
        prior = conn.execute(
            "select count(*) as n from publication_revisions where id = %s",
            (published.revision_id,),
        ).fetchone()
        assert row is not None and row["state"] == "corrected"
        assert replacement is not None and str(row["replacement_revision_id"]) == replacement
        assert prior is not None and prior["n"] == 1


def test_concurrent_publish_serializes(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="lock-co")

    def _once(_index: int) -> str:
        with _connect(db_url) as conn:
            result = publish_run(conn, run_id, actor="cli:local")
            conn.commit()
            return result.revision_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(_once, range(2)))
    assert ids[0] != ids[1]
    with _connect(db_url) as conn:
        n = conn.execute("select count(*) as n from publication_revisions").fetchone()
    assert n is not None and n["n"] == 2


def test_publish_stats_has_integer_counts(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="stats-co")
    with _connect(db_url) as conn:
        publish_run(conn, run_id, actor="cli:local")
        conn.commit()
        stats = publish_stats(conn)
    assert stats["published_revisions"] >= 1
    assert "postgresql://" not in str(stats)
