"""Structured data-practice schema.

This is the product. Diff these objects, not 40-page privacy PDFs.
Taxonomy follows OPP-115 / Polisis categories, flattened for LLM extraction.
Every practice MUST include a verbatim quote from the policy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DataType = Literal[
    "email",
    "name",
    "phone",
    "address",
    "location",
    "device_id",
    "ip_address",
    "browsing",
    "purchase",
    "payment",
    "contacts",
    "photos",
    "voice",
    "biometrics",
    "health",
    "messages",
    "account_activity",
    "inferred_profile",
    "other",
]

Purpose = Literal[
    "product",
    "analytics",
    "advertising",
    "personalization",
    "security",
    "legal",
    "research",
    "unspecified",
]

Party = Literal["first", "third"]
CollectionMode = Literal["user_provided", "automatic", "inferred", "unspecified"]
Materiality = Literal["cosmetic", "material", "unknown"]


class Quote(BaseModel):
    text: str = Field(description="Verbatim span copied from the policy. Do not paraphrase.")
    section: str = Field(description="Nearest heading or section label.")


class DataPractice(BaseModel):
    party: Party
    data_types: list[DataType]
    purposes: list[Purpose]
    collection_mode: CollectionMode = "unspecified"
    third_parties: list[str] = Field(
        default_factory=list,
        description="Named companies or categories (e.g. 'advertising partners').",
    )
    retention: str = Field(default="unspecified")
    user_control: str = Field(default="unspecified")
    quotes: list[Quote]


class PracticeDocument(BaseModel):
    company: str
    practices: list[DataPractice]
    notes: str = Field(
        default="",
        description="Anything that did not fit the schema. Keep short.",
    )


class MaterialityJudgement(BaseModel):
    materiality: Materiality
    reason: str
    data_types_added: list[DataType] = Field(default_factory=list)
    data_types_removed: list[DataType] = Field(default_factory=list)
    headline: str = Field(
        description="One sentence a non-lawyer would understand. Empty if cosmetic.",
    )
    summary: str
    quotes: list[Quote] = Field(default_factory=list)
