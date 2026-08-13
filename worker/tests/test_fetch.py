from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import pytest

from privacyradar.fetch import HopResponse, fetch_policy_url
from privacyradar.robots import StaticRobots
from privacyradar.ssrf import SsrfError, SsrfPolicy, classify_url


class FakeResolver:
    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def resolve(self, hostname: str) -> list[str]:
        self.calls.append(hostname)
        if hostname not in self.mapping:
            raise SsrfError("dns")
        return list(self.mapping[hostname])


class FakeHop:
    def __init__(self, hops: list[HopResponse]) -> None:
        self.hops = list(hops)
        self.calls: list[str] = []

    def get(
        self,
        url: str,
        headers: dict[str, str],
        *,
        ip: str,
        hostname: str,
        port: int,
        scheme: str,
    ) -> HopResponse:
        self.calls.append(url)
        if not self.hops:
            raise AssertionError(f"unexpected hop {url}")
        return self.hops.pop(0)


PUBLIC_IP = "93.184.216.34"
POLICY_HTML = (
    "<html><body><article><h1>Privacy</h1>"
    "<p>We collect your email address to create an account.</p>"
    "</article></body></html>"
)


def test_fetch_ssrf_localhost_blocked_without_resolver_override() -> None:
    hop = FakeHop([HopResponse(200, {"content-type": "text/html"}, POLICY_HTML.encode())])
    result = fetch_policy_url(
        "http://127.0.0.1/",
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.error == "ssrf"
    assert hop.calls == []
    result = fetch_policy_url(
        "http://169.254.169.254/latest/meta-data/",
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.error == "ssrf"
    assert hop.calls == []


def test_robots_fetch_failure_fail_closed_on_default_checker() -> None:
    hop = FakeHop([HopResponse(0, {}, b"", error_code="timeout")])
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        resolver=resolver,
        hop_client=hop,
    )
    assert result.error == "robots"
    assert hop.calls == ["https://example.test/robots.txt"]
    hop = FakeHop([HopResponse(200, {"content-type": "text/html"}, POLICY_HTML.encode())])
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        resolver=resolver,
        robots=StaticRobots(False),
        hop_client=hop,
    )
    assert result.error == "robots"
    assert hop.calls == []


def test_conditional_304_from_hop() -> None:
    hop = FakeHop([HopResponse(304, {"etag": '"abc"'}, b"")])
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        etag='"abc"',
        resolver=resolver,
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.status == 304
    assert result.error is None
    assert result.body == b""
    assert result.etag == '"abc"'


def test_oversize_body_error_code() -> None:
    hop = FakeHop([HopResponse(200, {}, b"", error_code="oversize")])
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        resolver=resolver,
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.error == "oversize"


def test_ssrf_redirect_to_private_ip_does_not_follow() -> None:
    hop = FakeHop(
        [HopResponse(302, {"location": "http://127.0.0.1/secret"}, b"")]
    )
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        resolver=resolver,
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.error == "ssrf"
    assert hop.calls == ["https://example.test/privacy"]


def test_fetch_result_does_not_put_exception_message_in_error_code() -> None:
    hop = FakeHop([HopResponse(0, {}, b"", error_code="timeout")])
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    result = fetch_policy_url(
        "https://example.test/privacy",
        resolver=resolver,
        robots=StaticRobots(True),
        hop_client=hop,
    )
    assert result.error == "timeout"
    assert "Exception" not in (result.error or "")


class _FixtureHandler(BaseHTTPRequestHandler):
    routes: dict[str, Any] = {}

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        spec = self.routes.get(self.path, {"status": 404, "body": b"missing"})
        status = int(spec["status"])
        body: bytes = spec.get("body", b"")
        headers: dict[str, str] = spec.get("headers", {"Content-Type": "text/html"})
        if spec.get("sleep"):
            import time

            time.sleep(float(spec["sleep"]))
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if status != 304:
            self.wfile.write(body)


@pytest.fixture
def fixture_http() -> tuple[str, int, SsrfPolicy, FakeResolver]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    port = int(server.server_address[1])
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = "fixtures.privacyradar.test"
    policy = SsrfPolicy(
        allow_loopback_hosts=frozenset({host}),
        extra_ports=frozenset({port}),
    )
    resolver = FakeResolver({host: ["127.0.0.1"]})
    try:
        yield host, port, policy, resolver
    finally:
        server.shutdown()
        server.server_close()


def test_local_fixture_http_matrix(
    fixture_http: tuple[str, int, SsrfPolicy, FakeResolver],
) -> None:
    host, port, policy, resolver = fixture_http
    base = f"http://{host}:{port}"
    _FixtureHandler.routes = {
        "/ok": {
            "status": 200,
            "body": POLICY_HTML.encode(),
            "headers": {"Content-Type": "text/html", "ETag": '"v1"'},
        },
        "/not-modified": {"status": 304, "body": b"", "headers": {"ETag": '"v1"'}},
        "/go": {
            "status": 302,
            "body": b"",
            "headers": {"Location": f"{base}/ok"},
        },
        "/slow-ok": {
            "status": 429,
            "body": b"rate",
            "headers": {"Content-Type": "text/plain"},
        },
        "/down": {"status": 503, "body": b"nope", "headers": {"Content-Type": "text/plain"}},
        "/huge": {
            "status": 200,
            "body": b"x" * (5 * 1024 * 1024 + 8),
            "headers": {"Content-Type": "text/plain"},
        },
        "/pdf": {
            "status": 200,
            "body": b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n",
            "headers": {"Content-Type": "application/pdf"},
        },
        "/shell": {
            "status": 200,
            "body": (
                b"<html><body><div id='app'></div>"
                b"<script>window.__SSR=1</script></body></html>"
            ),
            "headers": {"Content-Type": "text/html"},
        },
    }
    robots = StaticRobots(True)

    ok = fetch_policy_url(
        f"{base}/ok", resolver=resolver, policy=policy, robots=robots
    )
    assert ok.status == 200
    assert ok.error is None
    assert b"email address" in ok.body
    assert ok.etag == '"v1"'

    not_mod = fetch_policy_url(
        f"{base}/not-modified", resolver=resolver, policy=policy, robots=robots
    )
    assert not_mod.status == 304

    redirected = fetch_policy_url(
        f"{base}/go", resolver=resolver, policy=policy, robots=robots
    )
    assert redirected.status == 200
    assert b"email address" in redirected.body

    limited = fetch_policy_url(
        f"{base}/slow-ok", resolver=resolver, policy=policy, robots=robots
    )
    assert limited.status == 429

    down = fetch_policy_url(
        f"{base}/down", resolver=resolver, policy=policy, robots=robots
    )
    assert down.status == 503

    huge = fetch_policy_url(
        f"{base}/huge", resolver=resolver, policy=policy, robots=robots
    )
    assert huge.error == "oversize"

    pdf = fetch_policy_url(
        f"{base}/pdf", resolver=resolver, policy=policy, robots=robots
    )
    assert pdf.status == 200
    assert "pdf" in pdf.content_type.lower()

    shell = fetch_policy_url(
        f"{base}/shell", resolver=resolver, policy=policy, robots=robots
    )
    assert shell.status == 200
    assert b"__SSR" in shell.body

    # Production classifier still rejects raw loopback URLs.
    with pytest.raises(SsrfError):
        classify_url("http://127.0.0.1/")
