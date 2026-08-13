from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from privacyradar import pipeline
from privacyradar.crawl import FetchResult
from privacyradar.hashing import doc_hash
from privacyradar.observe import observe_source
from privacyradar.testing.fakes import FakeAnalyzer, FakeFetcher
from privacyradar.testing.fixtures import make_company, make_source
from privacyradar.testing.persist import persist_company, persist_source

pytestmark = pytest.mark.integration

POLICY_A = "# Privacy\nWe collect your email address to create an account.\n"
POLICY_B = (
    "# Privacy\nWe collect your phone number to create an account.\n"
    "# Sharing\nWe share information with advertisers.\n"
)


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


def _seed(url: str, slug: str = "signal", region: str = "global") -> dict[str, object]:
    company = make_company(slug=slug)
    source = make_source(company, region=region)
    with _connect(url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        conn.commit()
    return {
        "source_id": str(source.id),
        "company_id": str(company.id),
        "slug": company.slug,
        "name": company.name,
        "url": source.url,
        "region": region,
    }


def _fetch(url: str, markdown: str, *, error: str | None = None, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        status=status if error is None else 0,
        content_type="text/html",
        html=f"<article>{markdown}</article>",
        markdown="" if error else markdown,
        error=error,
    )


def test_observe_success_persists_attempt_snapshot_observation(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline.settings, "database_url", db_url)
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")
    source = _seed(db_url, "signal")
    fetcher = FakeFetcher(pages={source["url"]: _fetch(str(source["url"]), POLICY_A)})
    result = pipeline.process_source(source, fetch=fetcher)
    assert "first snapshot stored" in result
    with _connect(db_url) as conn:
        snapshots = conn.execute("select * from snapshots").fetchall()
        attempts = conn.execute("select * from source_attempts").fetchall()
        observations = conn.execute("select * from observations").fetchall()
        policy = conn.execute(
            "select health_status, current_snapshot_id from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
    assert len(snapshots) == 1
    assert snapshots[0]["is_valid"] is True
    assert snapshots[0]["fetch_error"] is None
    assert snapshots[0]["doc_hash"] != "empty"
    assert len(attempts) == 1
    assert attempts[0]["status"] == "succeeded"
    assert len(observations) == 1
    assert policy is not None
    assert policy["health_status"] == "healthy"
    assert str(policy["current_snapshot_id"]) == str(snapshots[0]["id"])


def test_repeat_identical_fetch_dedupes_content(db_url: str) -> None:
    source = _seed(db_url, "dedupe-co")
    fetched = _fetch(str(source["url"]), POLICY_A)
    with _connect(db_url) as conn:
        first = observe_source(conn, source, fetched, clock=datetime(2026, 1, 15, 12, tzinfo=UTC))
        conn.commit()
        fetched_at = conn.execute("select fetched_at from snapshots").fetchone()
        second = observe_source(
            conn, source, fetched, clock=datetime(2026, 1, 15, 13, tzinfo=UTC)
        )
        conn.commit()
        snapshots = conn.execute("select id, fetched_at from snapshots").fetchall()
        attempts = conn.execute("select count(*) as n from source_attempts").fetchone()
        observations = conn.execute("select count(*) as n from observations").fetchone()
    assert first.outcome == "new_version"
    assert second.outcome == "deduped"
    assert len(snapshots) == 1
    assert fetched_at is not None
    assert snapshots[0]["fetched_at"] == fetched_at["fetched_at"]
    assert attempts is not None and attempts["n"] == 2
    assert observations is not None and observations["n"] == 1


def test_content_change_creates_document_change(db_url: str) -> None:
    source = _seed(db_url, "change-co")
    with _connect(db_url) as conn:
        observe_source(conn, source, _fetch(str(source["url"]), POLICY_A))
        conn.commit()
        result = observe_source(conn, source, _fetch(str(source["url"]), POLICY_B))
        conn.commit()
        changes = conn.execute("select * from document_changes").fetchall()
        snapshots = conn.execute("select id from snapshots order by fetched_at").fetchall()
        pointers = conn.execute(
            "select current_snapshot_id from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
    assert result.outcome == "new_version"
    assert len(snapshots) == 2
    assert len(changes) == 1
    assert "Sharing" in changes[0]["added_sections"]
    assert "Privacy" in changes[0]["modified_sections"]
    assert pointers is not None
    assert str(pointers["current_snapshot_id"]) == str(snapshots[1]["id"])


def test_recurrence_a_b_a_reuses_snapshot_a(db_url: str) -> None:
    source = _seed(db_url, "recurrence")
    clock = datetime(2026, 1, 15, 12, tzinfo=UTC)
    with _connect(db_url) as conn:
        observe_source(conn, source, _fetch(str(source["url"]), POLICY_A), clock=clock)
        conn.commit()
        observe_source(
            conn,
            source,
            _fetch(str(source["url"]), POLICY_B),
            clock=clock + timedelta(hours=1),
        )
        conn.commit()
        third = observe_source(
            conn,
            source,
            _fetch(str(source["url"]), POLICY_A),
            clock=clock + timedelta(hours=2),
        )
        conn.commit()
        snapshots = conn.execute(
            "select id, doc_hash from snapshots order by fetched_at"
        ).fetchall()
        observations = conn.execute(
            "select snapshot_id from observations order by observed_at"
        ).fetchall()
        attempts = conn.execute("select count(*) as n from source_attempts").fetchone()
        current = conn.execute(
            "select current_snapshot_id from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
        last_change = conn.execute(
            """
            select from_snapshot_id, to_snapshot_id, added_sections,
                   removed_sections, modified_sections
            from document_changes
            order by created_at desc
            limit 1
            """
        ).fetchone()
    assert len(snapshots) == 2
    assert attempts is not None and attempts["n"] == 3
    assert len(observations) == 3
    hash_a = doc_hash(POLICY_A)
    snapshot_a = next(row for row in snapshots if row["doc_hash"] == hash_a)
    snapshot_b = next(row for row in snapshots if row["doc_hash"] != hash_a)
    assert str(observations[0]["snapshot_id"]) == str(snapshot_a["id"])
    assert str(observations[1]["snapshot_id"]) == str(snapshot_b["id"])
    assert str(observations[2]["snapshot_id"]) == str(snapshot_a["id"])
    assert current is not None
    assert str(current["current_snapshot_id"]) == str(snapshot_a["id"])
    assert last_change is not None
    assert str(last_change["from_snapshot_id"]) == str(snapshot_b["id"])
    assert str(last_change["to_snapshot_id"]) == str(snapshot_a["id"])
    assert "Sharing" in last_change["removed_sections"]
    assert "Privacy" in last_change["modified_sections"]
    assert third.outcome == "new_version"


def test_failed_fetch_does_not_replace_current_snapshot(db_url: str) -> None:
    source = _seed(db_url, "timeout-co")
    with _connect(db_url) as conn:
        observe_source(conn, source, _fetch(str(source["url"]), POLICY_A))
        conn.commit()
        before = conn.execute(
            "select current_snapshot_id, health_status from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
        failed = observe_source(
            conn, source, _fetch(str(source["url"]), "", error="timeout")
        )
        conn.commit()
        after = conn.execute(
            """
            select current_snapshot_id, health_status, last_failure_code,
                   consecutive_failures, last_success_at
            from policy_sources where id = %s
            """,
            (source["source_id"],),
        ).fetchone()
        snapshots = conn.execute("select count(*) as n from snapshots").fetchone()
        observations = conn.execute("select count(*) as n from observations").fetchone()
        attempts = conn.execute(
            "select status, error_code from source_attempts order by started_at"
        ).fetchall()
    assert failed.outcome == "failed"
    assert failed.error_code == "timeout"
    assert before is not None and after is not None
    assert after["current_snapshot_id"] == before["current_snapshot_id"]
    assert after["health_status"] == "degraded"
    assert after["last_failure_code"] == "timeout"
    assert after["consecutive_failures"] == 1
    assert after["last_success_at"] is not None
    assert snapshots is not None and snapshots["n"] == 1
    assert observations is not None and observations["n"] == 1
    assert [row["status"] for row in attempts] == ["succeeded", "failed"]
    assert attempts[1]["error_code"] == "timeout"


def test_region_variants_are_not_merged(db_url: str) -> None:
    company = make_company(slug="region-co")
    global_source = make_source(company, region="global")
    eu_source = make_source(company, region="EU")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, global_source)
        persist_source(conn, eu_source)
        conn.commit()
    global_payload = {
        "source_id": str(global_source.id),
        "company_id": str(company.id),
        "slug": company.slug,
        "name": company.name,
        "url": global_source.url,
        "region": "global",
    }
    eu_payload = {
        "source_id": str(eu_source.id),
        "company_id": str(company.id),
        "slug": company.slug,
        "name": company.name,
        "url": eu_source.url,
        "region": "EU",
    }
    with _connect(db_url) as conn:
        observe_source(conn, global_payload, _fetch(global_source.url, POLICY_A))
        observe_source(conn, eu_payload, _fetch(eu_source.url, POLICY_A))
        conn.commit()
        snaps = conn.execute("select source_id, region from snapshots").fetchall()
    assert len(snaps) == 2
    assert {str(row["source_id"]) for row in snaps} == {
        str(global_source.id),
        str(eu_source.id),
    }
    assert {row["region"] for row in snaps} == {"global", "EU"}


def test_unique_source_hash_normalizer_rejects_duplicates(db_url: str) -> None:
    source = _seed(db_url, "unique-co")
    with _connect(db_url) as conn:
        observe_source(conn, source, _fetch(str(source["url"]), POLICY_A))
        conn.commit()
        snap = conn.execute("select id, doc_hash from snapshots").fetchone()
        assert snap is not None
        with pytest.raises(UniqueViolation):
            conn.execute(
                """
                insert into snapshots (
                  source_id, markdown, doc_hash, section_hashes, normalizer_version
                )
                values (%s, %s, %s, '{}'::jsonb, '1.0.0')
                """,
                (source["source_id"], POLICY_A, snap["doc_hash"]),
            )
            conn.commit()
        conn.rollback()


def test_append_only_triggers(db_url: str) -> None:
    source = _seed(db_url, "trigger-co")
    with _connect(db_url) as conn:
        observe_source(conn, source, _fetch(str(source["url"]), POLICY_A))
        conn.commit()
        with pytest.raises(psycopg.Error):
            conn.execute("update snapshots set markdown = %s", ("mutated",))
            conn.commit()
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("update observations set region = %s", ("mutated",))
            conn.commit()
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("delete from observations")
            conn.commit()
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("delete from snapshots")
            conn.commit()
        conn.rollback()


def test_observation_insert_failure_does_not_keep_current_pointer(db_url: str) -> None:
    source = _seed(db_url, "partial-co")
    with _connect(db_url) as conn:
        conn.execute(
            """
            create or replace function privacyradar_fail_observations()
            returns trigger language plpgsql as $$
            begin
              raise exception 'forced observation failure';
            end;
            $$;
            """
        )
        conn.execute("drop trigger if exists observations_fail on observations")
        conn.execute(
            """
            create trigger observations_fail
              before insert on observations
              for each row execute procedure privacyradar_fail_observations()
            """
        )
        conn.commit()
        with pytest.raises(psycopg.Error):
            observe_source(conn, source, _fetch(str(source["url"]), POLICY_A))
        conn.rollback()
        snaps = conn.execute("select count(*) as n from snapshots").fetchone()
        obs = conn.execute("select count(*) as n from observations").fetchone()
        pointer = conn.execute(
            "select current_snapshot_id from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
        conn.execute("drop trigger if exists observations_fail on observations")
        conn.commit()
    assert snaps is not None and snaps["n"] == 0
    assert obs is not None and obs["n"] == 0
    assert pointer is not None and pointer["current_snapshot_id"] is None


def test_concurrent_same_hash_one_snapshot(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline.settings, "database_url", db_url)
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")
    source = _seed(db_url, "race-co")
    fetched = _fetch(str(source["url"]), POLICY_A)

    def run(_index: int) -> str:
        return pipeline.process_source(
            source, fetch=FakeFetcher(pages={str(source["url"]): fetched})
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, range(2)))

    with _connect(db_url) as conn:
        snaps = conn.execute("select count(*) as n from snapshots").fetchone()
        attempts = conn.execute("select count(*) as n from source_attempts").fetchone()
        observations = conn.execute("select count(*) as n from observations").fetchone()
    assert snaps is not None and snaps["n"] == 1
    assert attempts is not None and attempts["n"] == 2
    assert observations is not None and observations["n"] == 1


def test_observe_does_not_call_model_to_compare_hashes(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline.settings, "database_url", db_url)
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")
    source = _seed(db_url, "no-llm")
    analyzer = FakeAnalyzer()
    fetcher = FakeFetcher(pages={str(source["url"]): _fetch(str(source["url"]), POLICY_A)})
    pipeline.process_source(
        source, fetch=fetcher, extract=analyzer.extract_practices, judge=analyzer.judge_materiality
    )
    pipeline.process_source(
        source, fetch=fetcher, extract=analyzer.extract_practices, judge=analyzer.judge_materiality
    )
    changed = FakeFetcher(pages={str(source["url"]): _fetch(str(source["url"]), POLICY_B)})
    pipeline.process_source(
        source, fetch=changed, extract=analyzer.extract_practices, judge=analyzer.judge_materiality
    )
    assert analyzer.judge_calls == 0
    assert analyzer.extract_calls == 0


def test_five_failures_quarantine_source(db_url: str) -> None:
    source = _seed(db_url, "quarantine-co")
    with _connect(db_url) as conn:
        for _ in range(5):
            observe_source(conn, source, _fetch(str(source["url"]), "", error="timeout"))
        conn.commit()
        row = conn.execute(
            "select health_status, consecutive_failures from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
    assert row is not None
    assert row["consecutive_failures"] == 5
    assert row["health_status"] == "quarantined"
