from io import BytesIO

from pypdf import PdfWriter

from privacyradar.classify import classify_fetch, safe_error_code
from privacyradar.crawl import FetchResult
from privacyradar.hashing import MIN_NORMALIZED_CHARS

LONG = "# Privacy\nWe collect your email address to create an account.\n"


def _fetched(**overrides: object) -> FetchResult:
    payload: dict[str, object] = {
        "url": "https://fixtures.privacyradar.test/privacy",
        "status": 200,
        "content_type": "text/html",
        "html": "<h1>Privacy</h1>",
        "markdown": LONG,
        "error": None,
        "body": b"",
    }
    payload.update(overrides)
    return FetchResult(**payload)  # type: ignore[arg-type]


def test_classify_valid_html() -> None:
    result = classify_fetch(_fetched())
    assert result.valid
    assert result.status == "succeeded"
    assert result.error_code is None
    assert result.normalized is not None
    assert len(result.normalized.markdown) >= MIN_NORMALIZED_CHARS


def test_classify_timeout() -> None:
    result = classify_fetch(_fetched(status=0, markdown="", error="timeout"))
    assert not result.valid
    assert result.error_code == "timeout"


def test_classify_http_errors() -> None:
    assert classify_fetch(_fetched(status=403, markdown="")).error_code == "http_4xx"
    assert classify_fetch(_fetched(status=404, markdown="")).error_code == "http_4xx"
    assert classify_fetch(_fetched(status=500, markdown="")).error_code == "http_5xx"


def test_classify_wrong_type() -> None:
    result = classify_fetch(
        _fetched(content_type="text/javascript", markdown="function x(){return 1;}")
    )
    assert result.error_code == "wrong_type"


def test_classify_empty_and_short() -> None:
    empty = classify_fetch(_fetched(markdown="", html="", body=b""))
    assert empty.error_code == "empty"
    short = classify_fetch(_fetched(markdown="too short", html="too short"))
    assert short.error_code == "short"


def test_classify_blank_pdf_is_not_a_valid_snapshot() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    result = classify_fetch(
        _fetched(content_type="application/pdf", html="", markdown="", body=buffer.getvalue())
    )
    assert not result.valid
    assert result.error_code in {"empty", "short", "normalize_failed"}


def test_classify_pdf_with_extracted_text() -> None:
    from pathlib import Path

    body = (Path(__file__).resolve().parent / "corpus" / "normalize" / "policy.pdf").read_bytes()
    result = classify_fetch(
        _fetched(content_type="application/pdf", html="", markdown="", body=body)
    )
    assert result.valid
    assert result.normalized is not None
    assert "email address" in result.normalized.markdown.lower()


def test_safe_error_code_maps_dns_tls_blocked() -> None:
    assert safe_error_code("Name or service not known") == "dns"
    assert safe_error_code("SSL: CERTIFICATE_VERIFY_FAILED") == "tls"
    assert safe_error_code("blocked by robots") == "blocked"
    assert safe_error_code("weird boom") == "network"
    raw = "timeout: HTTPSConnectionPool(host='example.com', port=443)"
    code = safe_error_code(raw)
    assert code == "timeout"
    assert "HTTPSConnectionPool" not in code


def test_garbage_bytes_are_not_valid_snapshots() -> None:
    result = classify_fetch(
        _fetched(
            content_type="application/pdf",
            markdown="",
            html="",
            body=b"\x00\x01\xff\xfe not a pdf",
        )
    )
    assert not result.valid
    assert result.error_code in {"empty", "normalize_failed", "short"}
