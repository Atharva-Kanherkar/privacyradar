"""Fake network and model adapters. They never open sockets or call providers."""

from __future__ import annotations

from privacyradar.crawl import FetchResult
from privacyradar.schema import MaterialityJudgement, PracticeDocument


class FakeFetcher:
    def __init__(
        self,
        pages: dict[str, FetchResult] | None = None,
        errors: dict[str, str] | None = None,
    ) -> None:
        self.pages = pages or {}
        self.errors = errors or {}
        self.calls: list[str] = []

    def __call__(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self.errors:
            return FetchResult(
                url=url,
                status=0,
                content_type="",
                html="",
                markdown="",
                error=self.errors[url],
            )
        if url not in self.pages:
            raise AssertionError(f"unexpected fetch of {url}")
        return self.pages[url]


class FakeAnalyzer:
    def __init__(
        self,
        document: PracticeDocument | None = None,
        judgement: MaterialityJudgement | None = None,
        model: str = "fake-model",
    ) -> None:
        self.document = document
        self.judgement = judgement
        self.model = model
        self.extract_calls = 0
        self.judge_calls = 0

    def extract_practices(
        self, company: str, markdown: str
    ) -> tuple[PracticeDocument, str]:
        self.extract_calls += 1
        if self.document is None:
            raise RuntimeError("FakeAnalyzer has no PracticeDocument configured")
        return self.document, self.model

    def judge_materiality(
        self,
        company: str,
        old_markdown: str,
        new_markdown: str,
        changed: list[str],
    ) -> tuple[MaterialityJudgement, str]:
        self.judge_calls += 1
        if self.judgement is None:
            raise RuntimeError("FakeAnalyzer has no MaterialityJudgement configured")
        return self.judgement, self.model
