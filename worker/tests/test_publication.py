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
    publish_event,
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
        n = conn.execute("select count(*) as n from publication_revisions").fetchone()
        claims = conn.execute("select count(*) as n from published_claims").fetchone()
        assert n is not None and n["n"] == 0
        assert claims is not None and claims["n"] == 0


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
        with pytest.raises(PublicationError, match="offset_mismatch"):
            publish_run(conn, run_id, actor="cli:local")
        n = conn.execute("select count(*) as n from publication_revisions").fetchone()
        assert n is not None and n["n"] == 0


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
    _, _, run_id = _seed_run(db_url, slug="atomic-co")
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
            values (%s, %s, 'atomkey', 'data_collected', 'email', 'disclosed', 1, 'valid')
            """,
            (bad_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (%s, %s, %s, 'absent quote', 'missing')
            """,
            (str(uuid4()), bad_id, str(snap["snapshot_id"])),
        )
        with pytest.raises(PublicationError):
            publish_run(conn, run_id, actor="cli:local")
        revs = conn.execute("select count(*) as n from publication_revisions").fetchone()
        published = conn.execute("select count(*) as n from published_claims").fetchone()
        assert revs is not None and revs["n"] == 0
        assert published is not None and published["n"] == 0


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
        with pytest.raises(PublicationError, match="snapshot_mismatch"):
            publish_run(conn, run_id, actor="cli:local")
        n = conn.execute("select count(*) as n from publication_revisions").fetchone()
        assert n is not None and n["n"] == 0


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


def test_publish_event_promotes_review_pending(db_url: str) -> None:
    from psycopg.types.json import Json

    company_id, observation_id, _run_id = _seed_run(db_url, slug="event-co")
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
              materiality, headline, summary, quotes, publication_state
            )
            values (%s, %s, %s, %s, 'material', 'Held change', 's', %s, 'review_pending')
            returning id
            """,
            (
                company_id,
                str(source["id"]),
                str(snap["snapshot_id"]),
                str(snap["snapshot_id"]),
                Json([{"text": QUOTE, "section": "Privacy"}]),
            ),
        ).fetchone()
        assert event is not None
        publish_event(conn, str(event["id"]), actor="cli:local")
        conn.commit()
        row = conn.execute(
            "select publication_state, published_at from change_events where id = %s",
            (str(event["id"]),),
        ).fetchone()
        assert row is not None
        assert row["publication_state"] == "published"
        assert row["published_at"] is not None


def test_publish_event_empty_quotes_refused(db_url: str) -> None:
    from psycopg.types.json import Json

    company_id, observation_id, _run_id = _seed_run(db_url, slug="empty-quotes-co")
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
              materiality, headline, summary, quotes, publication_state
            )
            values (%s, %s, %s, %s, 'material', 'No cites', 's', %s, 'review_pending')
            returning id
            """,
            (
                company_id,
                str(source["id"]),
                str(snap["snapshot_id"]),
                str(snap["snapshot_id"]),
                Json([]),
            ),
        ).fetchone()
        assert event is not None
        with pytest.raises(PublicationError, match="quote_missing"):
            publish_event(conn, str(event["id"]), actor="cli:local")
        row = conn.execute(
            "select publication_state from change_events where id = %s",
            (str(event["id"]),),
        ).fetchone()
        assert row is not None and row["publication_state"] == "review_pending"


def test_multi_span_claim_publishes_once(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="multispans-co")
    with _connect(db_url) as conn:
        claim = conn.execute(
            """
            select c.id, r.snapshot_id
            from candidate_claims c
            join extraction_runs r on r.id = c.run_id
            where r.id = %s
            """,
            (run_id,),
        ).fetchone()
        assert claim is not None
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (%s, %s, %s, %s, 'exact')
            """,
            (str(uuid4()), str(claim["id"]), str(claim["snapshot_id"]), QUOTE),
        )
        result = publish_run(conn, run_id, actor="cli:local")
        conn.commit()
        n = conn.execute(
            "select count(*) as n from published_claims where revision_id = %s",
            (result.revision_id,),
        ).fetchone()
        assert result.n_claims == 1
        assert n is not None and n["n"] == 1


def test_rollback_restores_prior_change_event(db_url: str) -> None:
    from psycopg.types.json import Json

    company_id, observation_id, run_id = _seed_run(db_url, slug="roll-event-co")
    with _connect(db_url) as conn:
        source = conn.execute(
            "select id from policy_sources where company_id = %s", (company_id,)
        ).fetchone()
        snap = conn.execute(
            "select snapshot_id from observations where id = %s", (observation_id,)
        ).fetchone()
        assert source is not None and snap is not None

        def _event(headline: str) -> str:
            row = conn.execute(
                """
                insert into change_events (
                  company_id, source_id, from_snapshot, to_snapshot,
                  materiality, headline, summary, quotes, publication_state
                )
                values (%s, %s, %s, %s, 'material', %s, 's', %s, 'review_pending')
                returning id
                """,
                (
                    company_id,
                    str(source["id"]),
                    str(snap["snapshot_id"]),
                    str(snap["snapshot_id"]),
                    headline,
                    Json([{"text": QUOTE, "section": "Privacy"}]),
                ),
            ).fetchone()
            assert row is not None
            return str(row["id"])

        event_a = _event("First")
        event_b = _event("Second")
        first = publish_run(conn, run_id, actor="cli:local", change_event_id=event_a)
        second = publish_run(conn, run_id, actor="cli:local", change_event_id=event_b)
        rollback_revision(conn, second.revision_id, actor="cli:local", reason="bad_rev")
        conn.commit()
        current = conn.execute(
            """
            select change_event_id from publication_revisions
            where state = 'published' order by revision_n desc limit 1
            """
        ).fetchone()
        assert current is not None
        assert str(current["change_event_id"]) == event_a
        assert first.revision_id != second.revision_id
        state_a = conn.execute(
            "select publication_state from change_events where id = %s", (event_a,)
        ).fetchone()
        state_b = conn.execute(
            "select publication_state from change_events where id = %s", (event_b,)
        ).fetchone()
        assert state_a is not None and state_a["publication_state"] == "published"
        assert state_b is not None and state_b["publication_state"] == "corrected"


def test_rollback_only_revision_clears_current(db_url: str) -> None:
    from psycopg.types.json import Json

    company_id, observation_id, run_id = _seed_run(db_url, slug="sole-roll-co")
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
              materiality, headline, summary, quotes, publication_state
            )
            values (%s, %s, %s, %s, 'material', 'Only pub', 's', %s, 'review_pending')
            returning id
            """,
            (
                company_id,
                str(source["id"]),
                str(snap["snapshot_id"]),
                str(snap["snapshot_id"]),
                Json([{"text": QUOTE, "section": "Privacy"}]),
            ),
        ).fetchone()
        assert event is not None
        published = publish_run(
            conn, run_id, actor="cli:local", change_event_id=str(event["id"])
        )
        rollback_revision(conn, published.revision_id, actor="cli:local", reason="bad_rev")
        conn.commit()
        current = conn.execute(
            """
            select count(*) as n
            from publication_revisions pr
            where pr.company_id = %s
              and pr.state = 'published'
              and not exists (
                select 1 from publication_revisions rb where rb.rolls_back_id = pr.id
              )
            """,
            (company_id,),
        ).fetchone()
        state = conn.execute(
            "select publication_state from change_events where id = %s",
            (str(event["id"]),),
        ).fetchone()
        marker = conn.execute(
            "select rolls_back_id from publication_revisions where state = 'rolled_back'"
        ).fetchone()
        assert current is not None and current["n"] == 0
        assert state is not None and state["publication_state"] == "corrected"
        assert marker is not None and str(marker["rolls_back_id"]) == published.revision_id


def test_normalized_quote_can_publish(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="norm-quote-co")
    with _connect(db_url) as conn:
        snap = conn.execute(
            "select snapshot_id from extraction_runs where id = %s", (run_id,)
        ).fetchone()
        assert snap is not None
        claim_id = str(uuid4())
        conn.execute(
            """
            insert into candidate_claims (
              id, run_id, claim_key, category, attribute, polarity,
              confidence, validation_state
            )
            values (%s, %s, 'normkey', 'data_collected', 'name', 'disclosed', 1, 'valid')
            """,
            (claim_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (
              %s, %s, %s,
              'We collect   your email address to create an account.',
              'normalized'
            )
            """,
            (str(uuid4()), claim_id, str(snap["snapshot_id"])),
        )
        result = publish_run(conn, run_id, actor="cli:local")
        conn.commit()
        row = conn.execute(
            """
            select quote, start_offset, end_offset from published_claims
            where revision_id = %s and claim_key = 'normkey'
            """,
            (result.revision_id,),
        ).fetchone()
        assert row is not None
        assert QUOTE in str(row["quote"]) or str(row["quote"]).find("email") >= 0
        assert int(row["start_offset"]) >= 0
        assert int(row["end_offset"]) > int(row["start_offset"])
        assert POLICY[int(row["start_offset"]) : int(row["end_offset"])] == str(row["quote"])


def test_failed_publish_persists_reject_audit(db_url: str) -> None:
    _, _, run_id = _seed_run(db_url, slug="persist-audit-co")
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
            values (%s, %s, 'persistkey', 'data_collected', 'email', 'disclosed', 1, 'valid')
            """,
            (bad_id, run_id),
        )
        conn.execute(
            """
            insert into evidence_spans (
              id, claim_id, snapshot_id, quote, validation_result
            )
            values (%s, %s, %s, 'absent quote', 'missing')
            """,
            (str(uuid4()), bad_id, str(snap["snapshot_id"])),
        )
        with pytest.raises(PublicationError, match="quote_missing"):
            publish_run(conn, run_id, actor="cli:local")
        conn.commit()
    with _connect(db_url) as conn:
        stats = publish_stats(conn)
        assert stats["citation_failures"] >= 1
        assert stats["published_revisions"] == 0


def test_publication_txn_commits_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import contextlib

    from privacyradar.cli import _publication_txn

    class FakeConn:
        def __init__(self) -> None:
            self.commits = 0

        def commit(self) -> None:
            self.commits += 1

    fake = FakeConn()
    monkeypatch.setattr(
        "privacyradar.cli.connect",
        lambda: contextlib.nullcontext(fake),
    )
    with pytest.raises(PublicationError, match="quote_missing"):
        _publication_txn(_raise_quote_missing)
    assert fake.commits == 1


def _raise_quote_missing(_conn: object) -> None:
    raise PublicationError("quote_missing")
