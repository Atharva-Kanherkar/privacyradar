from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import trafilatura

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


def fetch_url(url: str) -> FetchResult:
    headers = {
        "User-Agent": settings.crawl_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0, headers=headers) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        return FetchResult(
            url=url,
            status=0,
            content_type="",
            html="",
            markdown="",
            error=str(exc),
        )

    content_type = response.headers.get("content-type", "")
    body = response.content
    html = ""
    markdown = ""
    error: str | None = None
    if "pdf" in content_type.lower():
        from privacyradar.normalize import pdf_to_text

        markdown = pdf_to_text(body)
        if not markdown.strip():
            error = "empty"
    else:
        html = response.text
        markdown = (
            trafilatura.extract(
                html,
                url=str(response.url),
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )
            or ""
        )
        markdown = markdown.strip()
        if not markdown:
            error = "empty"

    return FetchResult(
        url=str(response.url),
        status=response.status_code,
        content_type=content_type,
        html=html,
        markdown=markdown,
        error=error,
        body=body,
    )


def polite_pause() -> None:
    time.sleep(settings.crawl_delay_seconds)
