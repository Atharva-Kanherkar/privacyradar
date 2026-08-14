from __future__ import annotations

import pytest

from privacyradar.extract_live import (
    LiveClaim,
    LiveExtraction,
    LiveQuote,
    claims_from_parsed,
    default_extractor,
)
from privacyradar.settings import settings


def test_claims_from_parsed_maps_quotes() -> None:
    parsed = LiveExtraction(
        claims=[
            LiveClaim(
                category="data_collected",
                attribute="email",
                polarity="disclosed",
                quotes=[LiveQuote(text="We collect your email address.", section="Privacy")],
                confidence=0.9,
            )
        ]
    )
    claims = claims_from_parsed(parsed)
    assert len(claims) == 1
    assert claims[0].category == "data_collected"
    assert claims[0].quotes[0].text == "We collect your email address."
    assert claims[0].confidence == 0.9


def test_default_extractor_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        default_extractor()
