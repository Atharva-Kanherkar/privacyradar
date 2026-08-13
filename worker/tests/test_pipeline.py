from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock

import pytest

from privacyradar import pipeline
from privacyradar.crawl import FetchResult

SOURCE: dict[str, Any] = {
    "source_id": "source-1",
    "company_id": "company-1",
    "slug": "example",
    "name": "Example",
    "url": "https://example.com/privacy",
}


@contextmanager
def fake_connection() -> Any:
    yield Mock()


def result(
    *, markdown: str = "# Privacy\nWe collect email.", error: str | None = None
) -> FetchResult:
    return FetchResult(
        url=SOURCE["url"],
        status=200,
        content_type="text/html",
        html="<h1>Privacy</h1>",
        markdown=markdown,
        error=error,
    )


def test_process_source_stores_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: result(markdown="", error="timeout"))
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(pipeline.db, "latest_snapshot", lambda *_args: None)
    insert_snapshot = Mock(return_value={"id": "snapshot-1"})
    monkeypatch.setattr(pipeline.db, "insert_snapshot", insert_snapshot)

    assert pipeline.process_source(SOURCE) == "example: fetch failed (timeout)"
    assert insert_snapshot.call_args.kwargs["error"] == "timeout"


def test_process_source_skips_unchanged_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched = result()
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: fetched)
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(
        pipeline.db,
        "latest_snapshot",
        lambda *_args: {
            "id": "snapshot-1",
            "doc_hash": pipeline.doc_hash(fetched.markdown),
            "markdown": fetched.markdown,
        },
    )
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")

    assert "unchanged" in pipeline.process_source(SOURCE)


def test_process_source_stores_first_snapshot_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: result())
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(pipeline.db, "latest_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        pipeline.db, "insert_snapshot", Mock(return_value={"id": "snapshot-1"})
    )
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")

    assert pipeline.process_source(SOURCE).endswith("skipped LLM (no key)")


def test_crawl_all_pauses_between_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(
        pipeline.db,
        "fetch_enabled_sources",
        lambda _conn: [SOURCE, {**SOURCE, "slug": "second"}],
    )
    process = Mock(side_effect=["first", "second"])
    pause = Mock()
    monkeypatch.setattr(pipeline, "process_source", process)
    monkeypatch.setattr(pipeline, "polite_pause", pause)

    assert pipeline.crawl_all() == ["first", "second"]
    pause.assert_called_once_with()
