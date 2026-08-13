from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar import pipeline
from privacyradar.crawl import FetchResult
from privacyradar.testing.fakes import FakeFetcher
from privacyradar.testing.fixtures import make_company, make_source
from privacyradar.testing.persist import persist_company, persist_source

pytestmark = pytest.mark.integration


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


def _source_row(company_slug: str = "signal") -> tuple[dict[str, object], object, object]:
    company = make_company(slug=company_slug)
    source = make_source(company)
    payload = {
        "source_id": str(source.id),
        "company_id": str(company.id),
        "slug": company.slug,
        "name": company.name,
        "url": source.url,
    }
    return payload, company, source


def test_process_source_with_fakes_persists_snapshot(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline.settings, "database_url", db_url)
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")
    payload, company, source = _source_row("signal")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        conn.commit()

    markdown = "# Privacy\nWe collect your email address to create an account.\n"
    fetcher = FakeFetcher(
        pages={
            source.url: FetchResult(
                url=source.url,
                status=200,
                content_type="text/html",
                html="<h1>Privacy</h1>",
                markdown=markdown,
            )
        }
    )

    result = pipeline.process_source(payload, fetch=fetcher)

    assert "first snapshot stored" in result
    with _connect(db_url) as conn:
        row = conn.execute(
            "select markdown, fetch_error, doc_hash from snapshots where source_id = %s",
            (str(source.id),),
        ).fetchone()
    assert row is not None
    assert row["markdown"] == markdown
    assert row["fetch_error"] is None
    assert row["doc_hash"] != "empty"
    assert fetcher.calls == [source.url]


def test_process_source_fetch_failure_does_not_look_like_empty_success(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline.settings, "database_url", db_url)
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")
    payload, company, source = _source_row("timeout-co")
    with _connect(db_url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        conn.commit()

    fetcher = FakeFetcher(errors={source.url: "timeout"})
    result = pipeline.process_source(payload, fetch=fetcher)

    assert "fetch failed (timeout)" in result
    with _connect(db_url) as conn:
        row = conn.execute(
            "select fetch_error, markdown from snapshots where source_id = %s",
            (str(source.id),),
        ).fetchone()
    assert row is not None
    assert row["fetch_error"] == "timeout"
    assert row["markdown"] == ""
