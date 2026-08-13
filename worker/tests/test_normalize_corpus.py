import json
from pathlib import Path

from privacyradar.hashing import doc_hash, normalize_markdown
from privacyradar.normalize import decode_body, html_to_markdown, pdf_to_text

CORPUS = Path(__file__).resolve().parent / "corpus" / "normalize"
EXPECTED = json.loads((CORPUS / "expected.json").read_text())


def test_golden_html_banner_and_nav_are_stripped() -> None:
    html = (CORPUS / "banner_nav.html").read_text()
    markdown = html_to_markdown(html, url="https://fixtures.privacyradar.test/privacy")
    lowered = markdown.lower()
    assert "email address" in lowered
    assert "accept cookies" not in lowered
    assert "careers" not in lowered
    assert doc_hash(markdown) == EXPECTED["banner_nav.html"]


def test_golden_encoding_and_line_endings() -> None:
    raw = (CORPUS / "encoding.html").read_bytes()
    text = decode_body(raw, "text/html; charset=utf-8")
    markdown = html_to_markdown(text)
    assert "email address" in markdown.lower()
    assert doc_hash(markdown) == EXPECTED["encoding.html"]
    crlf_source = text.replace("\n", "\r\n")
    assert doc_hash(html_to_markdown(crlf_source)) == EXPECTED["encoding.html"]
    assert doc_hash(markdown) == doc_hash(normalize_markdown(markdown.replace("\n", "\r\n")))


def test_golden_pdf_extracts_policy_text() -> None:
    extracted = pdf_to_text((CORPUS / "policy.pdf").read_bytes())
    assert "email address" in extracted.lower()
    assert doc_hash(extracted) == EXPECTED["policy.pdf"]
