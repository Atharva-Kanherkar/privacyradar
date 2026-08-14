from privacyradar.crawl import FetchResult, fetch_url


def test_fetch_url_delegates_to_safe_client(monkeypatch: object) -> None:
    import privacyradar.fetch as fetch_mod

    def fake_fetch(url: str, **_kwargs: object) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            content_type="text/html",
            html="<h1>Privacy</h1>",
            markdown="",
            error=None,
            body=b"<h1>Privacy</h1>",
        )

    monkeypatch.setattr(fetch_mod, "fetch_policy_url", fake_fetch)
    fetched = fetch_url("https://example.test/privacy")
    assert fetched.status == 200
    assert fetched.error is None
    assert fetched.body.startswith(b"<h1>")


def test_fetch_url_returns_structured_network_error(monkeypatch: object) -> None:
    import privacyradar.fetch as fetch_mod

    def fake_fetch(url: str, **_kwargs: object) -> FetchResult:
        return FetchResult(
            url=url,
            status=0,
            content_type="",
            html="",
            markdown="",
            error="network",
            body=b"",
        )

    monkeypatch.setattr(fetch_mod, "fetch_policy_url", fake_fetch)
    fetched = fetch_url("https://example.test/privacy")
    assert fetched.status == 0
    assert fetched.error == "network"
    assert "offline" not in (fetched.error or "")
