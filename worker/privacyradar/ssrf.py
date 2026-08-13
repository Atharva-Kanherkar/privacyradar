"""SSRF defenses for catalog policy fetches. Users cannot supply URLs."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
MAX_REDIRECTS = 3
MAX_BODY_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 30.0
CGNAT = ipaddress.ip_network("100.64.0.0/10")
METADATA_V4 = ipaddress.ip_address("169.254.169.254")
METADATA_V6 = ipaddress.ip_address("fd00:ec2::254")


class SsrfError(ValueError):
    """URL is not safe to fetch. Always maps to error_code `ssrf`."""

    error_code = "ssrf"


class Resolver(Protocol):
    def resolve(self, hostname: str) -> list[str]:
        """Return IP literals for hostname. Must not follow application redirects."""


@dataclass(frozen=True)
class SsrfPolicy:
    """Production policy allows no loopback. Tests may allow named fixture hosts."""

    allow_loopback_hosts: frozenset[str] = frozenset()
    extra_ports: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ResolvedTarget:
    url: str
    hostname: str
    port: int
    scheme: str
    ip: str
    ips: tuple[str, ...]


class DnsResolver:
    def resolve(self, hostname: str) -> list[str]:
        try:
            infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise SsrfError("dns") from exc
        addresses: list[str] = []
        seen: set[str] = set()
        for info in infos:
            sockaddr = info[4]
            raw_ip = sockaddr[0]
            if not isinstance(raw_ip, str):
                continue
            if raw_ip not in seen:
                seen.add(raw_ip)
                addresses.append(raw_ip)
        if not addresses:
            raise SsrfError("dns")
        return addresses


def is_blocked_ip(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return True
    if addr.version == 6 and addr.ipv4_mapped is not None:
        return is_blocked_ip(str(addr.ipv4_mapped))
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        or addr in (METADATA_V4, METADATA_V6)
    ):
        return True
    return bool(addr.version == 4 and addr in CGNAT)


def registrable_domain(hostname: str) -> str:
    host = hostname.lower().rstrip(".")
    if host.startswith("[") and host.endswith("]"):
        return host
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def classify_url(
    url: str,
    *,
    resolver: Resolver | None = None,
    policy: SsrfPolicy | None = None,
) -> ResolvedTarget:
    """Reject non-public, non-http(s), credentialed, or odd-port URLs."""
    dns = resolver or DnsResolver()
    rules = policy or SsrfPolicy()
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SsrfError("ssrf")
    if parsed.username is not None or parsed.password is not None:
        raise SsrfError("ssrf")
    port = parsed.port if parsed.port is not None else _default_port(parsed.scheme)
    hostname = parsed.hostname
    if not hostname:
        raise SsrfError("ssrf")

    ips: list[str]
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        ips = dns.resolve(hostname)
    else:
        ips = [str(literal)]

    if not ips:
        raise SsrfError("ssrf")

    host_key = hostname.lower().rstrip(".")
    port_ok = port in ALLOWED_PORTS or (
        host_key in rules.allow_loopback_hosts and port in rules.extra_ports
    )
    if not port_ok:
        raise SsrfError("ssrf")
    if host_key not in rules.allow_loopback_hosts:
        if parsed.scheme == "http" and port != 80:
            raise SsrfError("ssrf")
        if parsed.scheme == "https" and port != 443:
            raise SsrfError("ssrf")
    for ip in ips:
        if _allowed_loopback(host_key, ip, rules):
            continue
        if is_blocked_ip(ip):
            raise SsrfError("ssrf")

    normalized = parsed._replace(netloc=parsed.netloc.lower(), fragment="").geturl()
    return ResolvedTarget(
        url=normalized,
        hostname=hostname.lower().rstrip("."),
        port=port,
        scheme=parsed.scheme,
        ip=ips[0],
        ips=tuple(ips),
    )


def _allowed_loopback(hostname: str, ip: str, policy: SsrfPolicy) -> bool:
    if hostname not in policy.allow_loopback_hosts:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return bool(addr.is_loopback)


def classify_redirect(
    current_url: str,
    location: str,
    *,
    resolver: Resolver | None = None,
    policy: SsrfPolicy | None = None,
) -> ResolvedTarget:
    if not location or location.strip() == "":
        raise SsrfError("ssrf")
    joined = urljoin(current_url, location)
    return classify_url(joined, resolver=resolver, policy=policy)
