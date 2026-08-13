from pathlib import Path

from privacyradar.hashing import doc_hash, normalize_markdown
from privacyradar.normalize import decode_body, html_to_markdown, pdf_to_text

CORPUS = Path(__file__).resolve().parent / "corpus" / "normalize"


def test_golden_html_banner_and_nav_are_stripped() -> None:
    html = (CORPUS / "banner_nav.html").read_text()
    markdown = html_to_markdown(html, url="https://fixtures.privacyradar.test/privacy")
    assert "email address" in markdown.lower()
    lowered = markdown.lower()
    assert "accept cookies" not in lowered
    assert doc_hash(markdown) == doc_hash(normalize_markdown(markdown))


def test_golden_encoding_and_line_endings() -> None:
    html = (CORPUS / "encoding.html").read_bytes()
    text = decode_body(html, "text/html; charset=utf-8")
    markdown = html_to_markdown(text)
    assert "email address" in markdown.lower()
    crlf = markdown.replace("\n", "\r\n")
    assert doc_hash(markdown) == doc_hash(crlf)


def test_pdf_bytes_extract_does_not_raise() -> None:
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    extracted = pdf_to_text(buffer.getvalue())
    assert isinstance(extracted, str)
    assert "traceback" not in extracted.lower()
