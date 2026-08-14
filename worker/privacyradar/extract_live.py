"""Live OpenAI extractor adapter. Tests inject FakeExtractor instead."""

from __future__ import annotations

from openai import OpenAI
from pydantic import BaseModel, Field

from privacyradar.claims import CandidateClaim, EvidenceQuote
from privacyradar.settings import settings

MAX_INPUT_CHARS = 120_000


class LiveQuote(BaseModel):
    text: str = Field(description="Verbatim span copied from the untrusted policy region.")
    section: str = Field(default="", description="Nearest heading or section label.")


class LiveClaim(BaseModel):
    category: str
    attribute: str
    polarity: str
    quotes: list[LiveQuote]
    confidence: float = 0.0


class LiveExtraction(BaseModel):
    claims: list[LiveClaim]


def claims_from_parsed(parsed: LiveExtraction) -> list[CandidateClaim]:
    return [
        CandidateClaim(
            category=item.category,
            attribute=item.attribute,
            polarity=item.polarity,
            quotes=[EvidenceQuote(text=quote.text, section=quote.section) for quote in item.quotes],
            confidence=item.confidence,
        )
        for item in parsed.claims
    ]


class LiveExtractor:
    def extract(
        self,
        *,
        instructions: str,
        document: str,
        taxonomy_version: str,
        model: str,
    ) -> list[CandidateClaim]:
        del taxonomy_version
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=settings.openai_api_key)
        parsed = client.responses.parse(
            model=model,
            instructions=instructions,
            input=document[:MAX_INPUT_CHARS],
            text_format=LiveExtraction,
        )
        if parsed.output_parsed is None:
            raise RuntimeError("OpenAI returned no parsed claims")
        return claims_from_parsed(parsed.output_parsed)


def default_extractor() -> LiveExtractor:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return LiveExtractor()
