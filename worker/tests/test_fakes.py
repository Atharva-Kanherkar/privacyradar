from privacyradar.crawl import FetchResult
from privacyradar.schema import MaterialityJudgement, PracticeDocument, Quote
from privacyradar.testing.fakes import FakeAnalyzer, FakeFetcher


def test_fake_fetcher_returns_configured_results_and_errors() -> None:
    url = "https://fixtures.privacyradar.test/signal/privacy"
    page = FetchResult(
        url=url,
        status=200,
        content_type="text/html",
        html="<h1>Privacy</h1>",
        markdown="# Privacy\nWe collect email.",
        error=None,
    )
    fetcher = FakeFetcher(pages={url: page}, errors={"https://timeout.test": "timeout"})

    assert fetcher(url).markdown == "# Privacy\nWe collect email."
    failed = fetcher("https://timeout.test")
    assert failed.error == "timeout"
    assert failed.markdown == ""
    assert fetcher.calls == [url, "https://timeout.test"]


def test_fake_fetcher_rejects_unexpected_urls() -> None:
    fetcher = FakeFetcher()
    try:
        fetcher("https://unexpected.example.test")
    except AssertionError as exc:
        assert "unexpected fetch" in str(exc)
    else:
        raise AssertionError("expected unexpected fetch to fail")


def test_fake_analyzer_returns_configured_practices_and_judgement() -> None:
    document = PracticeDocument(company="Signal", practices=[])
    judgement = MaterialityJudgement(
        materiality="cosmetic",
        reason="date stamp",
        headline="",
        summary="No material change",
        quotes=[Quote(text="Updated January 2026", section="Intro")],
    )
    analyzer = FakeAnalyzer(document=document, judgement=judgement)

    parsed, model = analyzer.extract_practices("Signal", "policy")
    judged, judge_model = analyzer.judge_materiality("Signal", "old", "new", ["Intro"])

    assert parsed is document
    assert judged is judgement
    assert model == "fake-model"
    assert judge_model == "fake-model"
    assert analyzer.extract_calls == 1
    assert analyzer.judge_calls == 1


def test_fake_analyzer_requires_configured_outputs() -> None:
    analyzer = FakeAnalyzer()
    try:
        analyzer.extract_practices("Signal", "policy")
    except RuntimeError as exc:
        assert "PracticeDocument" in str(exc)
    else:
        raise AssertionError("expected missing document to fail")
    try:
        analyzer.judge_materiality("Signal", "old", "new", [])
    except RuntimeError as exc:
        assert "MaterialityJudgement" in str(exc)
    else:
        raise AssertionError("expected missing judgement to fail")
