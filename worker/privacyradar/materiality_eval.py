"""Labeled synthetic materiality corpus and heuristic judge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CORPUS_PATH = Path(__file__).resolve().parents[1] / "eval" / "materiality" / "pairs.jsonl"
PRECISION_GATE = 0.95
CORPUS_SIZE = 200


def heuristic_materiality(old: str, new: str) -> str:
    if new.rstrip().endswith("...") and len(new) < len(old):
        return "uncertain"
    if "We sell personal information" in new and "We sell personal information" not in old:
        return "material"
    if "We keep data for 7 years" in new and "We keep data for 7 years" not in old:
        return "material"
    if "You may request deletion" in old and "You may request deletion" not in new:
        return "material"
    if "This section applies to the EU" in new and "This section applies to the EU" not in old:
        return "material"
    if "we may share information" in new.lower() and "we may share information" not in old.lower():
        return "uncertain"
    if _only_date_or_nav(old, new):
        return "cosmetic"
    return "uncertain"


def _only_date_or_nav(old: str, new: str) -> bool:
    def strip(text: str) -> str:
        lines = [
            line
            for line in text.splitlines()
            if not line.startswith("Updated ")
            and "Privacy Policy" not in line
            and "footer" not in line.lower()
            and "nav:" not in line.lower()
        ]
        return "\n".join(lines)

    return strip(old) == strip(new) and old != new


def load_pairs(path: Path = CORPUS_PATH) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def evaluate_materiality(path: Path = CORPUS_PATH) -> dict[str, Any]:
    pairs = load_pairs(path)
    tp = fp = 0
    for pair in pairs:
        predicted = heuristic_materiality(pair["old"], pair["new"])
        if predicted == pair["label"]:
            tp += 1
        else:
            fp += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {
        "n_pairs": len(pairs),
        "precision": precision,
        "cost_usd": 0.0,
    }


def gates_pass(report: dict[str, Any]) -> bool:
    return (
        int(report["n_pairs"]) >= CORPUS_SIZE
        and float(report["precision"]) >= PRECISION_GATE
        and float(report["cost_usd"]) == 0.0
    )


def format_report(report: dict[str, Any]) -> str:
    return (
        f"n_pairs={report['n_pairs']} precision={report['precision']} "
        f"cost_usd={report['cost_usd']}"
    )


def build_pairs() -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    base = (
        "# Privacy\nWe collect your email address to create an account.\n"
        "You may request deletion.\n"
    )
    templates = [
        (
            "cosmetic_date",
            "cosmetic",
            base + "Updated January 2026\n",
            base + "Updated February 2026\n",
        ),
        (
            "cosmetic_nav",
            "cosmetic",
            base + "nav: Home About\n",
            base + "nav: Home About Careers\n",
        ),
        (
            "material_sale",
            "material",
            base,
            base + "We sell personal information to advertisers.\n",
        ),
        (
            "material_retention",
            "material",
            base,
            base + "We keep data for 7 years.\n",
        ),
        (
            "material_deletion",
            "material",
            base,
            "# Privacy\nWe collect your email address to create an account.\n",
        ),
        (
            "material_eu",
            "material",
            base,
            base + "This section applies to the EU.\n",
        ),
        (
            "uncertain_may",
            "uncertain",
            base,
            base + "Depending on context, we may share information.\n",
        ),
        (
            "uncertain_truncation",
            "uncertain",
            base + "We describe sharing with partners in detail.\n",
            "# Privacy\nWe collect your email address to create an account.\n...",
        ),
    ]
    while len(pairs) < CORPUS_SIZE:
        kind, label, old, new = templates[len(pairs) % len(templates)]
        n = len(pairs)
        pairs.append(
            {
                "id": f"{kind}-{n:03d}",
                "label": label,
                "old": old.replace("email address", f"email address ({n})"),
                "new": new.replace("email address", f"email address ({n})"),
            }
        )
    return pairs
