from __future__ import annotations

from pathlib import Path

from privacyradar.eval_runner import evaluate_golden, format_report, gates_pass


def test_golden_extraction_eval_meets_gates() -> None:
    report = evaluate_golden()
    assert report["n_fixtures"] >= 12
    assert gates_pass(report)
    text = format_report(report)
    assert "citation_validity=" in text
    assert "postgresql://" not in text
    assert "OPENAI" not in text
    assert "We collect" not in text


def test_public_company_sql_does_not_select_candidate_claims() -> None:
    source = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "db.ts"
    text = source.read_text()
    assert "candidate_claims" not in text
    assert "extraction_runs" not in text
    assert "evidence_spans" not in text
