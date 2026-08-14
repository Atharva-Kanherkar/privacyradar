from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.claims import CandidateClaim, EvidenceQuote
from privacyradar.extract import extract_observation
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
        outcome = extract_observation(conn, observation_id, FixedExtractor())
        conn.commit()
        assert outcome is not None
        with pytest.raises(psycopg.Error):
            conn.execute(
                "update extraction_runs set model = 'tamper' where id = %s",
                (outcome.run_id,),
            )
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("delete from extraction_runs where id = %s", (outcome.run_id,))


def test_failed_observation_does_not_create_candidates(db_url: str) -> None:
    with _connect(db_url) as conn:
        missing = extract_observation(
            conn, "00000000-0000-0000-0000-000000000000", FixedExtractor()
        )
        count = conn.execute("select count(*) as n from candidate_claims").fetchone()
    assert missing is None
    assert count is not None and count["n"] == 0
