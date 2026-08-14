"""Deterministic extraction evaluation over synthetic golden fixtures."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from privacyradar.claims import CandidateClaim, EvidenceQuote
from privacyradar.extract import extract_document
from privacyradar.taxonomy import TAXONOMY_VERSION, claim_key

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "eval" / "golden"

CITATION_GATE = 1.0
UNSUPPORTED_GATE = 0.0
PR_GATE = 0.99
LATENCY_GATE_MS = 5000


class GoldenExtractor:
    """Returns the adjudicated expected claims for a fixture. No network."""

    def __init__(self, expected: list[CandidateClaim]) -> None:
        self.expected = expected

    def extract(
        self,
        *,
        instructions: str,
        document: str,
        taxonomy_version: str,
        model: str,
    ) -> list[CandidateClaim]:
        del instructions, taxonomy_version, model
        return [
            claim
            for claim in self.expected
            if any(quote.text in document for quote in claim.quotes)
        ]


def _load_expected(path: Path) -> list[CandidateClaim]:
    payload = json.loads(path.read_text())
    claims: list[CandidateClaim] = []
    for item in payload["claims"]:
        quotes = [
            EvidenceQuote(text=quote["text"], section=quote.get("section", ""))
            for quote in item.get("quotes", [])
        ]
        claims.append(
            CandidateClaim(
                category=item["category"],
                attribute=item["attribute"],
                polarity=item["polarity"],
                quotes=quotes,
                confidence=1.0,
                claim_key=claim_key(
                    taxonomy_version=TAXONOMY_VERSION,
                    category=item["category"],
                    attribute=item["attribute"],
                    polarity=item["polarity"],
                ),
            )
        )
    return claims


def _keys(claims: list[CandidateClaim]) -> set[str]:
    return {claim.claim_key for claim in claims if claim.validation_state == "valid"}


def evaluate_golden(golden_dir: Path = GOLDEN_DIR) -> dict[str, Any]:
    started = time.perf_counter()
    fixtures = sorted(golden_dir.glob("*.expected.json"))
    tp_by: dict[str, int] = defaultdict(int)
    fp_by: dict[str, int] = defaultdict(int)
    fn_by: dict[str, int] = defaultdict(int)
    citations = 0
    citation_ok = 0
    unsupported = 0
    total_valid = 0
    for expected_path in fixtures:
        stem = expected_path.name.removesuffix(".expected.json")
        markdown = (golden_dir / f"{stem}.md").read_text()
        expected = _load_expected(expected_path)
        predicted = extract_document(markdown, GoldenExtractor(expected))
        exp_keys = _keys(expected)
        pred_keys = _keys(predicted)
        for claim in predicted:
            total_valid += 1
            if claim.validation_state != "valid":
                unsupported += 1
            for quote in claim.quotes:
                citations += 1
                if quote.text in markdown or " ".join(quote.text.split()) in " ".join(
                    markdown.split()
                ):
                    citation_ok += 1
        categories = {claim.category for claim in expected + predicted}
        for category in categories:
            exp_c = {c.claim_key for c in expected if c.category == category}
            pred_c = {
                c.claim_key
                for c in predicted
                if c.category == category and c.validation_state == "valid"
            }
            tp_by[category] += len(exp_c & pred_c)
            fp_by[category] += len(pred_c - exp_c)
            fn_by[category] += len(exp_c - pred_c)
        del exp_keys, pred_keys
    latency_ms = int((time.perf_counter() - started) * 1000)
    precision_by = {}
    recall_by = {}
    for category in sorted(set(tp_by) | set(fp_by) | set(fn_by)):
        tp = tp_by[category]
        fp = fp_by[category]
        fn = fn_by[category]
        precision_by[category] = tp / (tp + fp) if (tp + fp) else 1.0
        recall_by[category] = tp / (tp + fn) if (tp + fn) else 1.0
    overall_tp = sum(tp_by.values())
    overall_fp = sum(fp_by.values())
    overall_fn = sum(fn_by.values())
    precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) else 1.0
    recall = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) else 1.0
    citation_validity = citation_ok / citations if citations else 0.0
    unsupported_rate = unsupported / total_valid if total_valid else 0.0
    return {
        "precision_by_category": precision_by,
        "recall_by_category": recall_by,
        "precision": precision,
        "recall": recall,
        "citation_validity": citation_validity,
        "unsupported_claim_rate": unsupported_rate,
        "latency_ms": latency_ms,
        "cost_usd": 0.0,
        "n_fixtures": len(fixtures),
    }


def gates_pass(report: dict[str, Any]) -> bool:
    return (
        float(report["citation_validity"]) >= CITATION_GATE
        and float(report["unsupported_claim_rate"]) <= UNSUPPORTED_GATE
        and float(report["precision"]) >= PR_GATE
        and float(report["recall"]) >= PR_GATE
        and int(report["latency_ms"]) < LATENCY_GATE_MS
        and float(report["cost_usd"]) == 0.0
    )


def format_report(report: dict[str, Any]) -> str:
    return (
        f"citation_validity={report['citation_validity']}"
        f" unsupported_claim_rate={report['unsupported_claim_rate']}"
        f" precision={report['precision']}"
        f" recall={report['recall']}"
        f" latency_ms={report['latency_ms']}"
        f" cost_usd={report['cost_usd']}"
        f" n_fixtures={report['n_fixtures']}"
    )
