from __future__ import annotations

from pathlib import Path

from privacyradar.eval_runner import (
    GOLDEN_DIR,
    GoldenExtractor,
    _load_expected,
    evaluate_golden,
    format_report,
    gates_pass,
)
from privacyradar.extract import extract_document


def test_golden_extraction_eval_meets_gates() -> None:
    report = evaluate_golden()
    assert report["n_fixtures"] >= 12
    assert report["citation_validity"] == 1.0
    assert report["unsupported_claim_rate"] == 0.0
    assert report["precision"] >= 0.99
    assert report["recall"] >= 0.99
    assert report["cost_usd"] == 0.0
    assert gates_pass(report)
    text = format_report(report)
    assert "citation_validity=" in text
    assert "postgresql://" not in text
    assert "OPENAI" not in text
    assert "We collect" not in text


def test_gates_pass_rejects_subthreshold() -> None:
    base = evaluate_golden()
    assert gates_pass(base)
    assert not gates_pass({**base, "citation_validity": 0.99})
    assert not gates_pass({**base, "unsupported_claim_rate": 0.01})
    assert not gates_pass({**base, "precision": 0.98})
    assert not gates_pass({**base, "recall": 0.98})
    assert not gates_pass({**base, "latency_ms": 5000})
    assert not gates_pass({**base, "cost_usd": 0.01})


def test_golden_extractor_requires_quote_in_chunk() -> None:
    expected = _load_expected(GOLDEN_DIR / "long_tail.expected.json")
    extractor = GoldenExtractor(expected)
    empty = extractor.extract(
        instructions="x",
        document="filler without the disclosure",
        taxonomy_version="1.0.0",
        model="fake",
    )
    found = extractor.extract(
        instructions="x",
        document="We share identifiers with advertising partners.",
        taxonomy_version="1.0.0",
        model="fake",
    )
    assert empty == []
    assert len(found) == 1
    assert found[0].attribute == "advertising_partner"


def test_negated_sale_fixture_is_not_disclosed() -> None:
    markdown = (GOLDEN_DIR / "sharing_no_sale.md").read_text()
    expected = _load_expected(GOLDEN_DIR / "sharing_no_sale.expected.json")
    found = extract_document(markdown, GoldenExtractor(expected))
    assert len(found) == 1
    assert found[0].category == "sharing"
    assert found[0].attribute == "sale"
    assert found[0].polarity == "negated"
    assert found[0].validation_state == "valid"


def test_public_company_sql_does_not_select_candidate_claims() -> None:
    source = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "db.ts"
    text = source.read_text()
    assert "candidate_claims" not in text
    assert "extraction_runs" not in text
    assert "evidence_spans" not in text
