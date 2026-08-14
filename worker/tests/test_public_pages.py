from __future__ import annotations

from pathlib import Path

from privacyradar.testing.persist import seed_public_fixtures


def test_public_pages_sql_ignores_candidates() -> None:
    source = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "db.ts"
    text = source.read_text()
    assert "candidate_claims" not in text
    assert "extraction_runs" not in text
    assert "published_claims" in text
    assert "publication_state = 'published'" in text
    compare = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "compare.ts"
    compare_text = compare.read_text()
    assert "candidate_claims" not in compare_text
    assert "extraction_runs" not in compare_text
    pages = (Path(__file__).resolve().parents[2] / "web" / "src" / "app").rglob("*.tsx")
    joined = "\n".join(path.read_text() for path in pages)
    assert "extraction?.practices" not in joined
    assert "What they take" not in joined


def test_seed_public_fixtures_publishes_signal_claim(db_url: str) -> None:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        assert seed_public_fixtures(conn) == 2
        conn.commit()
        claims = conn.execute(
            """
            select count(*) as n from published_claims pc
            join publication_revisions pr on pr.id = pc.revision_id
            join companies c on c.id = pr.company_id
            where c.slug = 'signal'
              and pr.state = 'published'
              and not exists (
                select 1 from publication_revisions rb where rb.rolls_back_id = pr.id
              )
            """
        ).fetchone()
        published = conn.execute(
            """
            select headline from change_events
            where publication_state = 'published'
            """
        ).fetchone()
        unpublished = conn.execute(
            """
            select publication_state from change_events
            where headline = 'UNPUBLISHED_FIXTURE_HEADLINE'
            """
        ).fetchone()
        assert claims is not None and claims["n"] == 1
        assert published is not None and published["headline"] == "PUBLISHED_FIXTURE_HEADLINE"
        assert unpublished is not None and unpublished["publication_state"] == "review_pending"
