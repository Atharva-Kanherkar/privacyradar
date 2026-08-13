from __future__ import annotations

import time
from dataclasses import dataclass

from privacyradar.settings import settings


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    html: str
    markdown: str
    error: str | None = None
    body: bytes = b""
    etag: str | None = None
    last_modified: str | None = None


def fetch_url(url: str) -> FetchResult:
    from privacyradar.fetch import fetch_policy_url

    return fetch_policy_url(url)


def polite_pause() -> None:
    time.sleep(settings.crawl_delay_seconds)
