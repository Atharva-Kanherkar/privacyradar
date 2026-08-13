"""Versioned document normalization. Pure functions; no network."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

import trafilatura
from pypdf import PdfReader

from privacyradar.hashing import (
    MIN_NORMALIZED_CHARS,
    NORMALIZER_VERSION,
    doc_hash,
    normalize_markdown,
    section_hashes,
)

HTML_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
)
PDF_TYPES = ("application/pdf", "application/x-pdf")


@dataclass(frozen=True)
class NormalizeResult:
    version: str
    markdown: str
    raw_sha256: str
    normalized_sha256: str
    section_hashes: dict[str, str]
    byte_count: int
    failed: bool
    error_code: str | None = None


def raw_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_body(body: bytes, content_type: str = "") -> str:
    charset = "utf-8"
    lowered = content_type.lower()
    if "charset=" in lowered:
        charset = lowered.split("charset=", 1)[1].split(";", 1)[0].strip().strip('"') or "utf-8"
    for encoding in (charset, "utf-8-sig", "utf-8", "latin-1"):
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def html_to_markdown(html: str, url: str = "") -> str:
    extracted = trafilatura.extract(
        html,
        url=url or None,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    return normalize_markdown(extracted or "")


def pdf_to_text(body: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(body))
        parts = [(page.extract_text() or "") for page in reader.pages]
    except Exception:
        return ""
    return normalize_markdown("\n".join(parts))


def media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def is_html_type(content_type: str) -> bool:
    return media_type(content_type) in HTML_TYPES or media_type(content_type) == ""


def is_pdf_type(content_type: str) -> bool:
    return media_type(content_type) in PDF_TYPES


def normalize_document(
    *,
    body: bytes = b"",
    html: str = "",
    markdown: str = "",
    content_type: str = "",
    url: str = "",
    version: str = NORMALIZER_VERSION,
) -> NormalizeResult:
    """Canonicalize fetched bytes/text under a named normalizer version."""
    raw = body if body else (html or markdown).encode("utf-8")
    digest_raw = raw_sha256(raw)
    byte_count = len(raw)
    try:
        if version != NORMALIZER_VERSION:
            return NormalizeResult(
                version=version,
                markdown="",
                raw_sha256=digest_raw,
                normalized_sha256="",
                section_hashes={},
                byte_count=byte_count,
                failed=True,
                error_code="normalize_failed",
            )
        if is_pdf_type(content_type) and body:
            text = pdf_to_text(body)
            if not text.strip() and markdown.strip():
                text = normalize_markdown(markdown)
        elif markdown.strip():
            text = normalize_markdown(markdown)
            if len(text.strip()) < MIN_NORMALIZED_CHARS and (html or body):
                source_html = html or decode_body(body, content_type)
                extracted = html_to_markdown(source_html, url=url)
                if len(extracted.strip()) > len(text.strip()):
                    text = extracted
        elif html or (body and is_html_type(content_type)):
            source_html = html or decode_body(body, content_type)
            text = html_to_markdown(source_html, url=url)
        else:
            text = normalize_markdown(html or decode_body(body, content_type))
        if not text.strip():
            return NormalizeResult(
                version=version,
                markdown="",
                raw_sha256=digest_raw,
                normalized_sha256="",
                section_hashes={},
                byte_count=byte_count,
                failed=True,
                error_code="empty",
            )
        return NormalizeResult(
            version=version,
            markdown=text,
            raw_sha256=digest_raw,
            normalized_sha256=doc_hash(text),
            section_hashes=section_hashes(text),
            byte_count=byte_count,
            failed=False,
        )
    except Exception:
        return NormalizeResult(
            version=version,
            markdown="",
            raw_sha256=digest_raw,
            normalized_sha256="",
            section_hashes={},
            byte_count=byte_count,
            failed=True,
            error_code="normalize_failed",
        )
