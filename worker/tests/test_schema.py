import pytest
from pydantic import ValidationError

from privacyradar.schema import DataPractice, MaterialityJudgement, PracticeDocument, Quote


def test_practice_document_accepts_supported_taxonomy() -> None:
    document = PracticeDocument(
        company="Example",
        practices=[
            DataPractice(
                party="first",
                data_types=["email", "ip_address"],
                purposes=["product", "security"],
                collection_mode="user_provided",
                quotes=[Quote(text="We collect your email address.", section="Collection")],
            )
        ],
    )

    assert document.practices[0].data_types == ["email", "ip_address"]


def test_practice_document_rejects_unknown_data_type() -> None:
    with pytest.raises(ValidationError):
        DataPractice(
            party="first",
            data_types=["favorite_dinosaur"],  # type: ignore[list-item]
            purposes=["product"],
            quotes=[Quote(text="Example", section="Collection")],
        )


def test_materiality_rejects_unknown_state() -> None:
    with pytest.raises(ValidationError):
        MaterialityJudgement(
            materiality="urgent",  # type: ignore[arg-type]
            reason="Unsupported state",
            headline="Headline",
            summary="Summary",
        )
