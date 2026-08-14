"""Robots.txt checks. Fail closed: a fetch error is not permission to crawl."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.robotparser import RobotFileParser

from privacyradar.settings import settings
from privacyradar.ssrf import ResolvedTarget

ROBOTS_CACHE_TTL = timedelta(hours=1)


class RobotsChecker(Protocol):
    def allowed(self, target: ResolvedTarget) -> bool:
        """Return True only when robots.txt explicitly allows the path."""


class StaticRobots:
    def __init__(self, allow: bool) -> None:
        self.allow = allow
        self.calls: list[str] = []

    def allowed(self, target: ResolvedTarget) -> bool:
        self.calls.append(target.url)
        return self.allow


class FailClosedRobots:
    """Used when robots.txt cannot be retrieved safely."""

    def allowed(self, target: ResolvedTarget) -> bool:
        return False


def path_allowed(robots_text: str, url: str, user_agent: str) -> bool:
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return bool(parser.can_fetch(user_agent, url))


class CachedRobots:
    def __init__(
        self,
        fetch_robots_text: Callable[[str], str | None],
        *,
        user_agent: str | None = None,
    ) -> None:
        self._fetch_robots_text = fetch_robots_text
        self._user_agent = user_agent or settings.crawl_user_agent
        self._cache: dict[str, tuple[str | None, datetime]] = {}

    def allowed(self, target: ResolvedTarget) -> bool:
        origin = f"{target.scheme}://{target.hostname}"
        if target.port not in {80, 443}:
            origin = f"{target.scheme}://{target.hostname}:{target.port}"
        now = datetime.now(UTC)
        cached = self._cache.get(origin)
        if cached is None or now - cached[1] >= ROBOTS_CACHE_TTL:
            robots_url = origin + "/robots.txt"
            try:
                text = self._fetch_robots_text(robots_url)
            except Exception:
                text = None
            self._cache[origin] = (text if isinstance(text, str) else None, now)
        text = self._cache[origin][0]
        if text is None:
            return False
        return path_allowed(text, target.url, self._user_agent)
