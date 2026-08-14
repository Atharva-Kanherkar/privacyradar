from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.claims import CandidateClaim, EvidenceQuote
from privacyradar.extract import extract_observation, persist_run
from privacyradar.testing.fixtures import make_company, make_observation, make_source
from privacyradar.testing.persist import persist_company, persist_observation, persist_source

pytestmark = pytest.mark.integration

POLICY = "# Privacy\nWe collect your email address to create an account.\n"


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
                quotes=[
                    EvidenceQuote(
                        text="We collect your email address to create an account.",
                        section="Privacy",
                    )
                ],
                confidence=1.0,
            )
        ]


def _seed_observation(db_url: str) -> str:
    company = make_company(slug="extract-co")
    source = make_source(company)
    observation = make_observation(source, markdown=POLICY)
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        persist_observation(conn, observation)
        conn.commit()
    return str(observation.id)


def test_reprocess_same_observation_new_taxonomy_keeps_old_run(db_url: str) -> None:
    observation_id = _seed_observation(db_url)
    with _connect(db_url) as conn:
        first = extract_observation(conn, observation_id, FixedExtractor())
        conn.execute(
            """
            insert into taxonomy_versions (version, schema_checksum)
            values ('1.0.1', 'abcd')
            """
        )
        second = extract_observation(
            conn, observation_id, FixedExtractor(), taxonomy_version="1.0.1"
        )
        conn.commit()
        runs = conn.execute(
            "select taxonomy_version from extraction_runs order by created_at"
        ).fetchall()
    assert first is not None and second is not None
    assert first.run_id != second.run_id
    assert [row["taxonomy_version"] for row in runs] == ["1.0.0", "1.0.1"]


def test_extraction_run_is_append_only(db_url: str) -> None:
    observation_id = _seed_observation(db_url)
    with _connect(db_url) as conn:
        first = extract_observation(conn, observation_id, FixedExtractor())
        second = extract_observation(conn, observation_id, FixedExtractor())
        conn.commit()
        assert first is not None and second is not None
        assert first.run_id != second.run_id
        count = conn.execute("select count(*) as n from extraction_runs").fetchone()
        assert count is not None and count["n"] == 2
        with pytest.raises(psycopg.Error):
            conn.execute(
                "update extraction_runs set model = 'tamper' where id = %s",
                (first.run_id,),
            )
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("delete from extraction_runs where id = %s", (first.run_id,))
        conn.rollback()
        remaining = conn.execute("select count(*) as n from extraction_runs").fetchone()
        assert remaining is not None and remaining["n"] == 2


def test_failed_observation_does_not_create_candidates(db_url: str) -> None:
    with _connect(db_url) as conn:
        missing = extract_observation(
            conn, "00000000-0000-0000-0000-000000000000", FixedExtractor()
        )
        count = conn.execute("select count(*) as n from candidate_claims").fetchone()
    assert missing is None
    assert count is not None and count["n"] == 0


def test_invalid_snapshot_does_not_create_candidates(db_url: str) -> None:
    company = make_company(slug="invalid-snap")
    source = make_source(company)
    snap_id = str(uuid4())
    attempt_id = str(uuid4())
    obs_id = str(uuid4())
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        conn.execute(
            """
            insert into snapshots (id, source_id, doc_hash, markdown, is_valid)
            values (%s, %s, 'invalid-hash', %s, false)
            """,
            (snap_id, str(source.id), POLICY),
        )
        conn.execute(
            """
            insert into source_attempts (
              id, source_id, started_at, status, request_url
            )
            values (%s, %s, now(), 'failed', %s)
            """,
            (attempt_id, str(source.id), source.url),
        )
        conn.execute(
            """
            insert into observations (
              id, source_id, snapshot_id, attempt_id, observed_at, region
            )
            values (%s, %s, %s, %s, now(), %s)
            """,
            (obs_id, str(source.id), snap_id, attempt_id, source.region),
        )
        conn.commit()
        refused = extract_observation(conn, obs_id, FixedExtractor())
        count = conn.execute("select count(*) as n from candidate_claims").fetchone()
    assert refused is None
    assert count is not None and count["n"] == 0


def test_invalid_polarity_persists_as_unspecified(db_url: str) -> None:
    observation_id = _seed_observation(db_url)
    with _connect(db_url) as conn:
        row = conn.execute(
            "select snapshot_id from observations where id = %s",
            (observation_id,),
        ).fetchone()
        assert row is not None
        claim = CandidateClaim(
            category="data_collected",
            attribute="email",
            polarity="hacked",
            quotes=[EvidenceQuote(text="We collect your email address to create an account.")],
            confidence=0.1,
            claim_key="k",
            validation_state="invalid_category",
        )
        persist_run(
            conn,
            observation_id=observation_id,
            snapshot_id=str(row["snapshot_id"]),
            claims=[claim],
            markdown=POLICY,
        )
        conn.commit()
        stored = conn.execute(
            "select polarity, validation_state, payload from candidate_claims"
        ).fetchone()
    assert stored is not None
    assert stored["polarity"] == "unspecified"
    assert stored["validation_state"] == "invalid_category"
    assert stored["payload"]["raw_polarity"] == "hacked"
