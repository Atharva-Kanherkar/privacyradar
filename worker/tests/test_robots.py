from __future__ import annotations

from privacyradar.robots import CachedRobots, FailClosedRobots, StaticRobots, path_allowed
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


def test_path_allowed_respects_star_agent() -> None:
    text = "User-agent: *\nDisallow: /privacy\nAllow: /\n"
    assert path_allowed(text, "https://example.test/privacy", "privacyradar/0.1") is False
    assert path_allowed(text, "https://example.test/about", "privacyradar/0.1") is True
