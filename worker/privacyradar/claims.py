"""Candidate claim types. Untrusted until citation validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceQuote:
    text: str
    section: str = ""


@dataclass
class CandidateClaim:
    category: str
    attribute: str
    polarity: str
    quotes: list[EvidenceQuote] = field(default_factory=list)
    confidence: float = 0.0
    claim_key: str = ""
    validation_state: str = "valid"
