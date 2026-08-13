"""Optional JS-render fallback after an HTTP shell/empty body."""

from __future__ import annotations

from collections.abc import Callable

from privacyradar.classify import classify_fetch
from privacyradar.crawl import FetchResult

RenderFn = Callable[[str], FetchResult | None]


def with_render_fallback(
    url: str,
    fetched: FetchResult,
    render: RenderFn | None,
    *,
    enabled: bool,
) -> FetchResult:
    if not enabled or render is None:
        return fetched
    classification = classify_fetch(fetched)
    if classification.error_code not in {"empty", "short"}:
        return fetched
    rendered = render(url)
    if rendered is None:
        return fetched
    return rendered
