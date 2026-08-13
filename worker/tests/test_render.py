from privacyradar.crawl import FetchResult
from privacyradar.render import with_render_fallback
from privacyradar.settings import settings

SHELL = "<html><body><div id='app'></div></body></html>"
POLICY = (
    "<html><body><article><h1>Privacy</h1>"
    "<p>We collect your email address to create an account.</p>"
    "</article></body></html>"
)


def test_js_shell_http_then_render_adapter_when_enabled(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(settings, "playwright_fallback", True)
    http = FetchResult(
        url="https://example.test/privacy",
        status=200,
        content_type="text/html",
        html=SHELL,
        markdown="",
        body=SHELL.encode(),
    )
    rendered = FetchResult(
        url="https://example.test/privacy",
        status=200,
        content_type="text/html",
        html=POLICY,
        markdown="",
        body=POLICY.encode(),
    )

    def render(_url: str) -> FetchResult:
        return rendered

    result = with_render_fallback(
        "https://example.test/privacy",
        http,
        render,
        enabled=True,
    )
    assert b"email address" in result.body

    skipped = with_render_fallback(
        "https://example.test/privacy",
        http,
        render,
        enabled=False,
    )
    assert skipped.body == http.body
