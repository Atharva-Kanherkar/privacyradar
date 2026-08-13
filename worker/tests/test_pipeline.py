from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock

import pytest

from privacyradar import pipeline
from privacyradar.crawl import FetchResult
from privacyradar.observe import ObserveMetrics, ObserveResult

SOURCE: dict[str, Any] = {
    "source_id": "source-1",
    "company_id": "company-1",
    "slug": "example",
    "name": "Example",
    "url": "https://example.com/privacy",
    "region": "global",
}


@contextmanager
def fake_connection() -> Any:
    yield Mock()


def result(
    *,
    markdown: str = "# Privacy\nWe collect email address to create accounts.",
    error: str | None = None,
) -> FetchResult:
    return FetchResult(
        url=SOURCE["url"],
        status=200,
        content_type="text/html",
        html="<h1>Privacy</h1>",
        markdown=markdown,
        error=error,
    )


def _observed(**overrides: Any) -> ObserveResult:
    payload: dict[str, Any] = {
        "outcome": "failed",
        "message": "example: fetch failed (timeout)",
        "error_code": "timeout",
        "attempt_id": "attempt-1",
        "snapshot_id": None,
        "observation_id": None,
        "document_change_id": None,
        "current_snapshot_id": None,
        "health_status": "degraded",
        "metrics": ObserveMetrics(fetch_attempts=1, failed_attempts=1),
    }
    payload.update(overrides)
    return ObserveResult(**payload)


def test_process_source_reports_classified_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: result(markdown="", error="timeout"))
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(pipeline, "observe_source", lambda *_args, **_kwargs: _observed())

    assert pipeline.process_source(SOURCE) == "example: fetch failed (timeout)"


def test_process_source_skips_unchanged_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched = result()
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: fetched)
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(
        pipeline,
        "observe_source",
        lambda *_args, **_kwargs: _observed(
            outcome="deduped",
            message="example: unchanged (abc1234567)",
            error_code=None,
            snapshot_id="snapshot-1",
            health_status="healthy",
            metrics=ObserveMetrics(fetch_attempts=1, deduped=1),
        ),
    )
    monkeypatch.setattr(pipeline.settings, "openai_api_key", "")

    assert "unchanged" in pipeline.process_source(SOURCE)


def test_process_source_stores_first_snapshot_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "fetch_url", lambda _url: result())
    monkeypatch.setattr(pipeline.db, "connect", fake_connection)
    monkeypatch.setattr(
        pipeline,
        "observe_source",
        lambda *_args, **_kwargs: _observed(
            outcome="new_version",
            message="example: first snapshot stored",
            error_code=None,
            snapshot_id="snapshot-1",
            observation_id="obs-1",
            document_change_id=None,
            health_status="healthy",
            metrics=ObserveMetrics(fetch_attempts=1, new_versions=1),
        ),
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
