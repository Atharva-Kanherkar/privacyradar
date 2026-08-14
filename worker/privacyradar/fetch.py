"""SSRF-safe policy fetch. Pins the resolved IP and re-checks every redirect hop."""

from __future__ import annotations

import http.client
import socket
import ssl
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from privacyradar.crawl import FetchResult
from privacyradar.robots import CachedRobots, RobotsChecker, StaticRobots
from privacyradar.settings import settings
from privacyradar.ssrf import (
    FETCH_TIMEOUT_SECONDS,
    MAX_BODY_BYTES,
    MAX_REDIRECTS,
    Resolver,
    SsrfError,
    SsrfPolicy,
    classify_redirect,
    classify_url,
)

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True)
class HopResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    error_code: str | None = None


class HopClient(Protocol):
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
        """GET one hop. Must connect to `ip`, using `hostname` for Host/SNI."""


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError | socket.timeout):
        return "timeout"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, socket.gaierror):
        return "dns"
    return "network"


def _path_query(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _host_header(hostname: str, port: int, scheme: str) -> str:
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return hostname
    return f"{hostname}:{port}"


class PinnedHopClient:
    """Connect to the classified IP; SNI/Host stay on the original hostname."""

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
        timeout = FETCH_TIMEOUT_SECONDS
        try:
            sock = socket.create_connection((ip, port), timeout=timeout)
            sock.settimeout(timeout)
            if scheme == "https":
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=hostname)
            conn = http.client.HTTPConnection(hostname, port, timeout=timeout)
            conn.sock = sock
            conn.request("GET", _path_query(url), headers=headers)
            response = conn.getresponse()
            header_map = {k.lower(): v for k, v in response.getheaders()}
            body = response.read(MAX_BODY_BYTES + 1)
            conn.close()
        except Exception as exc:
            return HopResponse(status_code=0, headers={}, body=b"", error_code=_safe_error(exc))
        if len(body) > MAX_BODY_BYTES:
            return HopResponse(
                status_code=response.status,
                headers=header_map,
                body=b"",
                error_code="oversize",
            )
        return HopResponse(status_code=response.status, headers=header_map, body=body)


def _failed(url: str, error: str, status: int = 0) -> FetchResult:
    return FetchResult(
        url=url,
        status=status,
        content_type="",
        html="",
        markdown="",
        error=error,
        body=b"",
    )


def fetch_policy_url(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    resolver: Resolver | None = None,
    policy: SsrfPolicy | None = None,
    robots: RobotsChecker | None = None,
    hop_client: HopClient | None = None,
) -> FetchResult:
    client = hop_client if hop_client is not None else PinnedHopClient()
    if robots is not None:
        robots_checker = robots
    else:
        def _load_robots(robots_url: str) -> str | None:
            document = fetch_policy_url(
                robots_url,
                resolver=resolver,
                policy=policy,
                robots=StaticRobots(True),
                hop_client=client,
            )
            if document.error or document.status != 200:
                return None
            return document.body.decode("utf-8", errors="replace")

        robots_checker = CachedRobots(_load_robots)
    try:
        target = classify_url(url, resolver=resolver, policy=policy)
    except SsrfError:
        return _failed(url, "ssrf")

    if not robots_checker.allowed(target):
        return _failed(target.url, "robots")

    headers = {
        "User-Agent": settings.crawl_user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/pdf;q=0.9,"
            "text/plain;q=0.8,*/*;q=0.1"
        ),
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "identity",
        "Host": _host_header(target.hostname, target.port, target.scheme),
        "Connection": "close",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    current = target
    redirects = 0
    while True:
        hop = client.get(
            current.url,
            headers,
            ip=current.ip,
            hostname=current.hostname,
            port=current.port,
            scheme=current.scheme,
        )
        if hop.error_code:
            return _failed(current.url, hop.error_code, hop.status_code)
        if hop.status_code in _REDIRECTS:
            location = hop.headers.get("location", "")
            redirects += 1
            if redirects > MAX_REDIRECTS:
                return _failed(current.url, "moved", hop.status_code)
            try:
                nxt = classify_redirect(
                    current.url, location, resolver=resolver, policy=policy
                )
            except SsrfError:
                return _failed(current.url, "ssrf", hop.status_code)
            current = nxt
            headers["Host"] = _host_header(current.hostname, current.port, current.scheme)
            continue

        content_type = hop.headers.get("content-type", "")
        html = ""
        if "html" in content_type.lower() or content_type == "":
            html = hop.body.decode("utf-8", errors="replace")
        result = FetchResult(
            url=current.url,
            status=hop.status_code,
            content_type=content_type,
            html=html,
            markdown="",
            error=None,
            body=hop.body,
            etag=hop.headers.get("etag"),
            last_modified=hop.headers.get("last-modified"),
        )
        return result
