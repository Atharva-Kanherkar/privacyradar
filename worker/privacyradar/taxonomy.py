"""Versioned consumer-decision taxonomy. Changing the lists requires a new version."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

TAXONOMY_VERSION = "1.0.0"
PROMPT_VERSION = "extract-1.0.0"

Category = Literal[
    "data_collected",
    "purpose",
    "sharing",
    "retention",
    "control",
    "sensitive",
    "region",
    "uncertainty",
]

Polarity = Literal["disclosed", "negated", "unspecified"]

ATTRIBUTES: dict[str, tuple[str, ...]] = {
    "data_collected": (
        "email",
        "name",
        "phone",
        "location",
        "device_id",
        "ip_address",
        "browsing",
        "purchase",
        "payment",
        "photos",
        "voice",
        "messages",
        "account_activity",
        "inferred_profile",
        "other",
    ),
    "purpose": (
        "product",
        "analytics",
        "advertising",
        "personalization",
        "security",
        "legal",
        "ai_training",
        "research",
        "unspecified",
    ),
    "sharing": ("sale", "third_party", "advertising_partner", "none_disclosed"),
    "retention": ("duration_disclosed", "unspecified"),
    "control": ("deletion", "opt_out", "access", "none_disclosed"),
    "sensitive": (
        "biometrics",
        "health",
        "children",
        "precise_location",
        "none_disclosed",
    ),
    "region": ("global", "EU", "US", "other"),
    "uncertainty": ("unknown",),
}

CATEGORIES: tuple[str, ...] = tuple(ATTRIBUTES.keys())


def taxonomy_document(version: str = TAXONOMY_VERSION) -> dict[str, object]:
    return {
        "version": version,
        "categories": {key: list(values) for key, values in ATTRIBUTES.items()},
    }


def taxonomy_checksum(version: str = TAXONOMY_VERSION) -> str:
    payload = json.dumps(taxonomy_document(version), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def claim_key(
    *,
    taxonomy_version: str,
    category: str,
    attribute: str,
    polarity: str,
) -> str:
    material = f"{taxonomy_version}|{category}|{attribute}|{polarity}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate_claim_shape(category: str, attribute: str, polarity: str) -> bool:
    if category not in ATTRIBUTES:
        return False
    if attribute not in ATTRIBUTES[category]:
        return False
    return polarity in {"disclosed", "negated", "unspecified"}
