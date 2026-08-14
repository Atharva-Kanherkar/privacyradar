from __future__ import annotations

from privacyradar.taxonomy import (
    TAXONOMY_VERSION,
    claim_key,
    taxonomy_checksum,
    validate_claim_shape,
)


def test_taxonomy_checksum_stable_for_1_0_0() -> None:
    assert taxonomy_checksum() == (
        "3ca634aef1ce3f94d860952aaae7c265cccc4c73c7d30dd544b92892b82f0908"
    )
    assert taxonomy_checksum() == taxonomy_checksum("1.0.0")


def test_claim_key_stable_across_runs() -> None:
    first = claim_key(
        taxonomy_version=TAXONOMY_VERSION,
        category="data_collected",
        attribute="email",
        polarity="disclosed",
    )
    second = claim_key(
        taxonomy_version=TAXONOMY_VERSION,
        category="data_collected",
        attribute="email",
        polarity="disclosed",
    )
    assert first == second
    assert len(first) == 64


def test_claim_key_changes_when_taxonomy_version_changes() -> None:
    base = claim_key(
        taxonomy_version="1.0.0",
        category="data_collected",
        attribute="email",
        polarity="disclosed",
    )
    other = claim_key(
        taxonomy_version="1.1.0",
        category="data_collected",
        attribute="email",
        polarity="disclosed",
    )
    assert base != other


def test_unknown_attribute_rejected() -> None:
    assert validate_claim_shape("data_collected", "email", "disclosed") is True
    assert validate_claim_shape("data_collected", "favorite_dinosaur", "disclosed") is False


def test_negated_sale_is_not_disclosed_sale() -> None:
    disclosed = claim_key(
        taxonomy_version=TAXONOMY_VERSION,
        category="sharing",
        attribute="sale",
        polarity="disclosed",
    )
    negated = claim_key(
        taxonomy_version=TAXONOMY_VERSION,
        category="sharing",
        attribute="sale",
        polarity="negated",
    )
    assert disclosed != negated
