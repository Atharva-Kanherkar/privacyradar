from __future__ import annotations

import pytest

from privacyradar.ssrf import (
    SsrfError,
    classify_redirect,
    classify_url,
    is_blocked_ip,
    registrable_domain,
)


class FakeResolver:
    def __init__(self, mapping: dict[str, list[str]] | None = None) -> None:
        self.mapping = mapping or {}
        self.calls: list[str] = []

    def resolve(self, hostname: str) -> list[str]:
        self.calls.append(hostname)
        if hostname not in self.mapping:
            raise SsrfError("dns")
        answers = self.mapping[hostname]
        if not answers:
            raise SsrfError("dns")
        # Support rebinding: successive calls can pop from a list-of-lists.
        if answers and isinstance(answers[0], list):
            sequence = self.mapping[hostname]
            if not sequence:
                raise SsrfError("dns")
            return list(sequence.pop(0))
        return list(answers)


PUBLIC_IP = "93.184.216.34"


def test_ssrf_rejects_file_and_ftp_schemes() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    with pytest.raises(SsrfError):
        classify_url("file:///etc/passwd", resolver=resolver)
    with pytest.raises(SsrfError):
        classify_url("ftp://example.test/privacy", resolver=resolver)


def test_ssrf_rejects_loopback_and_link_local_and_private_and_cgnat_and_metadata() -> None:
    assert is_blocked_ip("127.0.0.1")
    assert is_blocked_ip("::1")
    assert is_blocked_ip("10.0.0.5")
    assert is_blocked_ip("192.168.1.9")
    assert is_blocked_ip("172.16.0.1")
    assert is_blocked_ip("169.254.169.254")
    assert is_blocked_ip("169.254.1.1")
    assert is_blocked_ip("100.64.0.1")
    assert is_blocked_ip("fd00:ec2::254")
    assert is_blocked_ip("fc00::1")
    assert is_blocked_ip("224.0.0.1")
    assert is_blocked_ip("0.0.0.0")
    assert is_blocked_ip("::ffff:127.0.0.1")
    assert not is_blocked_ip(PUBLIC_IP)

    resolver = FakeResolver()
    for url in (
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.1.2.3/privacy",
        "http://[::1]/",
    ):
        if "localhost" in url:
            resolver = FakeResolver({"localhost": ["127.0.0.1"]})
        with pytest.raises(SsrfError):
            classify_url(url, resolver=resolver)


def test_ssrf_rejects_non_80_443_ports() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    with pytest.raises(SsrfError):
        classify_url("https://example.test:8443/privacy", resolver=resolver)
    with pytest.raises(SsrfError):
        classify_url("http://example.test:8080/privacy", resolver=resolver)


def test_ssrf_allows_public_https_example_via_injected_resolver() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    target = classify_url("https://example.test/privacy", resolver=resolver)
    assert target.hostname == "example.test"
    assert target.port == 443
    assert target.scheme == "https"
    assert target.ip == PUBLIC_IP
    assert resolver.calls == ["example.test"]


def test_ssrf_redirect_to_private_ip_blocked() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    first = classify_url("https://example.test/privacy", resolver=resolver)
    assert first.ip == PUBLIC_IP
    with pytest.raises(SsrfError):
        classify_redirect(first.url, "http://127.0.0.1/", resolver=resolver)


def test_ssrf_dns_rebinding_second_resolve_private_blocked() -> None:
    resolver = FakeResolver({"rebind.test": [[PUBLIC_IP], ["127.0.0.1"]]})
    first = classify_url("https://rebind.test/privacy", resolver=resolver)
    assert first.ip == PUBLIC_IP
    with pytest.raises(SsrfError):
        classify_url("https://rebind.test/privacy", resolver=resolver)


def test_ssrf_rejects_userinfo_and_empty_host() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    with pytest.raises(SsrfError):
        classify_url("https://user:pass@example.test/privacy", resolver=resolver)
    with pytest.raises(SsrfError):
        classify_url("https:///privacy", resolver=resolver)


def test_registrable_domain_uses_last_two_labels() -> None:
    assert registrable_domain("policies.example.test") == "example.test"
    assert registrable_domain("EXAMPLE.TEST") == "example.test"


def test_relative_redirect_stays_on_public_host() -> None:
    resolver = FakeResolver({"example.test": [PUBLIC_IP]})
    target = classify_redirect(
        "https://example.test/old",
        "/new",
        resolver=resolver,
    )
    assert target.hostname == "example.test"
    assert target.url.endswith("/new")
