from unittest.mock import Mock

import httpx
import pytest

from privacyradar import crawl


class FakeClient:
    def __init__(
        self,
        response: Mock | None = None,
        error: Exception | None = None,
        **_kwargs: object,
    ):
        self.response = response
        self.error = error

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def get(self, _url: str) -> Mock:
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def test_fetch_url_extracts_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock(
        text="<h1>Privacy</h1>",
        status_code=200,
        headers={"content-type": "text/html"},
        url="https://example.com/privacy",
    )
    monkeypatch.setattr(
        crawl.httpx,
        "Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )
    monkeypatch.setattr(crawl.trafilatura, "extract", lambda *_args, **_kwargs: "  policy text  ")

    fetched = crawl.fetch_url("https://example.com/privacy")

    assert fetched.markdown == "policy text"
    assert fetched.error is None


def test_fetch_url_returns_structured_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://example.com/privacy")
    error = httpx.ConnectError("offline", request=request)
    monkeypatch.setattr(crawl.httpx, "Client", lambda **kwargs: FakeClient(error=error, **kwargs))

    fetched = crawl.fetch_url("https://example.com/privacy")

    assert fetched.status == 0
    assert fetched.error == "offline"
