from __future__ import annotations

from datetime import UTC, datetime, timedelta

from privacyradar.robots import (
    ROBOTS_CACHE_TTL,
    CachedRobots,
    FailClosedRobots,
    StaticRobots,
    path_allowed,
)
from privacyradar.ssrf import ResolvedTarget


def _target(url: str = "https://example.test/privacy") -> ResolvedTarget:
    return ResolvedTarget(
        url=url,
        hostname="example.test",
        port=443,
        scheme="https",
        ip="93.184.216.34",
        ips=("93.184.216.34",),
    )


def test_robots_disallow_blocks_without_fetching_body() -> None:
    robots = StaticRobots(allow=False)
    assert robots.allowed(_target()) is False
    assert robots.calls == ["https://example.test/privacy"]


def test_robots_fetch_failure_fail_closed() -> None:
    def boom(_url: str) -> str | None:
        raise OSError("offline")

    checker = CachedRobots(boom)
    assert checker.allowed(_target()) is False
    assert FailClosedRobots().allowed(_target()) is False


def test_robots_cache_expires_after_ttl() -> None:
    calls: list[str] = []

    def load(_url: str) -> str:
        calls.append(_url)
        return "User-agent: *\nAllow: /\n"

    checker = CachedRobots(load)
    assert checker.allowed(_target()) is True
    assert checker.allowed(_target()) is True
    assert len(calls) == 1
    origin = "https://example.test"
    text, fetched_at = checker._cache[origin]
    checker._cache[origin] = (text, fetched_at - ROBOTS_CACHE_TTL - timedelta(seconds=1))
    assert checker.allowed(_target()) is True
    assert len(calls) == 2
    assert fetched_at.tzinfo is UTC or fetched_at.tzinfo is not None


def test_path_allowed_respects_star_agent() -> None:
    text = "User-agent: *\nDisallow: /privacy\nAllow: /\n"
    assert path_allowed(text, "https://example.test/privacy", "privacyradar/0.1") is False
    assert path_allowed(text, "https://example.test/about", "privacyradar/0.1") is True
