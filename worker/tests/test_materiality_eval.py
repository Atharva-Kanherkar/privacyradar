from __future__ import annotations

from pathlib import Path

from privacyradar.materiality_eval import (
    evaluate_materiality,
    format_report,
    gates_pass,
    heuristic_materiality,
    load_pairs,
)


def test_materiality_corpus_meets_gates() -> None:
    report = evaluate_materiality()
    assert report["n_pairs"] >= 200
    assert report["precision"] >= 0.95
    assert report["cost_usd"] == 0.0
    assert gates_pass(report)
    text = format_report(report)
    assert "n_pairs=" in text
    assert "postgresql://" not in text
    assert "We sell personal information" not in text


def test_gates_pass_rejects_small_corpus() -> None:
    base = evaluate_materiality()
    assert not gates_pass({**base, "n_pairs": 199})
    assert not gates_pass({**base, "precision": 0.94})
    assert not gates_pass({**base, "cost_usd": 0.01})


def test_heuristic_labels_sale_and_date() -> None:
    assert (
        heuristic_materiality(
            "We collect email.",
            "We collect email.\nWe sell personal information to advertisers.",
        )
        == "material"
    )
    assert (
        heuristic_materiality(
            "# Privacy\nWe collect email.\nUpdated January 2026\n",
            "# Privacy\nWe collect email.\nUpdated February 2026\n",
        )
        == "cosmetic"
    )


def test_corpus_labels_match_heuristic() -> None:
    for pair in load_pairs():
        assert heuristic_materiality(pair["old"], pair["new"]) == pair["label"]


def test_public_sql_ignores_unpublished_and_candidates() -> None:
    source = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "db.ts"
    text = source.read_text()
    assert "candidate_claims" not in text
    assert "extraction_runs" not in text
    assert "publication_state in ('published', 'corrected')" in text
