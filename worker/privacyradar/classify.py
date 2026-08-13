"""Deterministic fetch classification. AI is never consulted."""

from __future__ import annotations

from dataclasses import dataclass

from privacyradar.crawl import FetchResult
from privacyradar.hashing import MIN_NORMALIZED_CHARS, NORMALIZER_VERSION
from privacyradar.normalize import (
    NormalizeResult,
    is_html_type,
    is_pdf_type,
    normalize_document,
)

SAFE_ERROR_CODES = frozenset(
    {
        "timeout",
        "dns",
        "tls",
        "http_4xx",
        "http_5xx",
        "http_429",
        "empty",
        "short",
        "wrong_type",
        "normalize_failed",
        "network",
        "blocked",
        "robots",
        "ssrf",
        "oversize",
        "moved",
    }
)


@dataclass(frozen=True)
class Classification:
    valid: bool
    status: str
    error_code: str | None
    normalized: NormalizeResult | None
    not_modified: bool = False


def safe_error_code(value: str | None) -> str:
    if value in SAFE_ERROR_CODES:
        return value
    if not value:
        return "network"
    lowered = value.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "name or service not known" in lowered or "nodename" in lowered or "dns" in lowered:
        return "dns"
    if "ssl" in lowered or "tls" in lowered or "certificate" in lowered:
        return "tls"
    if "blocked" in lowered or "robots" in lowered:
        return "blocked"
    if "ssrf" in lowered:
        return "ssrf"
    if "oversize" in lowered or "too large" in lowered:
        return "oversize"
    return "network"


def classify_fetch(fetched: FetchResult) -> Classification:
    if fetched.error:
        code = safe_error_code(fetched.error)
        return Classification(valid=False, status="failed", error_code=code, normalized=None)

    status = fetched.status or 0
    if status <= 0:
        return Classification(
            valid=False, status="failed", error_code="network", normalized=None
        )
    if status == 304:
        return Classification(
            valid=True,
            status="succeeded",
            error_code=None,
            normalized=None,
            not_modified=True,
        )
    if status == 429:
        return Classification(
            valid=False, status="failed", error_code="http_429", normalized=None
        )
    if 400 <= status < 500:
        return Classification(
            valid=False, status="failed", error_code="http_4xx", normalized=None
        )
    if status >= 500:
        return Classification(
            valid=False, status="failed", error_code="http_5xx", normalized=None
        )
    if status < 200 or status >= 300:
        return Classification(
            valid=False, status="failed", error_code="http_4xx", normalized=None
        )

    content_type = fetched.content_type or ""
    if content_type and not is_html_type(content_type) and not is_pdf_type(content_type):
        return Classification(
            valid=False, status="failed", error_code="wrong_type", normalized=None
        )

    body = fetched.body if fetched.body else b""
    normalized = normalize_document(
        body=body,
        html=fetched.html,
        markdown=fetched.markdown,
        content_type=content_type,
        url=fetched.url,
        version=NORMALIZER_VERSION,
    )
    if normalized.failed:
        return Classification(
            valid=False,
            status="failed",
            error_code=normalized.error_code or "normalize_failed",
            normalized=normalized,
        )
    if len(normalized.markdown.strip()) < MIN_NORMALIZED_CHARS:
        return Classification(
            valid=False, status="failed", error_code="short", normalized=normalized
        )
    return Classification(
        valid=True, status="succeeded", error_code=None, normalized=normalized
    )
