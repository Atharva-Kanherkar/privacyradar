from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.compare import build_comparison, parse_company_slugs
from privacyradar.testing.persist import seed_public_fixtures

pytestmark = pytest.mark.integration


def test_compare_requires_two_to_four_companies() -> None:
    slugs, truncated = parse_company_slugs("signal")
    assert slugs == ["signal"]
    assert truncated is False
    many, truncated_many = parse_company_slugs("a,b,c,d,e")
    assert many == ["a", "b", "c", "d"]
    assert truncated_many is True


def test_compare_unknown_cell_is_not_favorable(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        conn.commit()
        payload = build_comparison(conn, ["signal", "proton"])
    sharing = next(row for row in payload["dimensions"] if row["category"] == "sharing")
    signal_cell = next(cell for cell in sharing["cells"] if cell["slug"] == "signal")
    assert signal_cell["state"] == "not_found_in_evidence"
    assert signal_cell["favorable"] is False
    assert "score" not in payload


def test_compare_payload_has_no_score(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        conn.commit()
        payload = build_comparison(conn, ["signal", "proton"])
    assert payload["status"] == "comparable"
    assert "score" not in payload
    assert "score" not in str(payload["companies"])


def test_compare_mixed_taxonomy_is_not_comparable(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        old = conn.execute(
            """
            select pr.id, pr.company_id, pr.observation_id, pr.extraction_run_id,
                   pr.change_event_id, pc.candidate_claim_id, pc.claim_key,
                   pc.category, pc.attribute, pc.polarity, pc.quote, pc.snapshot_id,
                   pc.start_offset, pc.end_offset
            from publication_revisions pr
            join published_claims pc on pc.revision_id = pr.id
            join companies c on c.id = pr.company_id
            where c.slug = 'proton'
            limit 1
            """
        ).fetchone()
        assert old is not None
        conn.execute(
            """
            insert into publication_revisions (
              company_id, observation_id, extraction_run_id, change_event_id,
              revision_n, state, actor, taxonomy_version
            )
            values (%s, %s, %s, %s, 2, 'published', 'cli:local', '9.9.9')
            """,
            (
                old["company_id"],
                old["observation_id"],
                old["extraction_run_id"],
                old["change_event_id"],
            ),
        )
        newer = conn.execute(
            """
            select id from publication_revisions
            where company_id = %s and revision_n = 2
            """,
            (old["company_id"],),
        ).fetchone()
        assert newer is not None
        conn.execute(
            """
            insert into published_claims (
              revision_id, candidate_claim_id, claim_key, category, attribute,
              polarity, quote, snapshot_id, start_offset, end_offset
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                newer["id"],
                old["candidate_claim_id"],
                old["claim_key"],
                old["category"],
                old["attribute"],
                old["polarity"],
                old["quote"],
                old["snapshot_id"],
                old["start_offset"],
                old["end_offset"],
            ),
        )
        conn.commit()
        payload = build_comparison(conn, ["signal", "proton"])
    assert payload["status"] == "not_comparable"
    assert payload["dimensions"] == []


def test_compare_mixed_region_is_conspicuous(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        seed_public_fixtures(conn)
        conn.execute(
            """
            update policy_sources
            set region = 'EU'
            where company_id = (select id from companies where slug = 'proton')
            """
        )
        conn.commit()
        payload = build_comparison(conn, ["signal", "proton"])
    assert payload["status"] == "comparable"
    assert payload["region_mismatch"] is True
