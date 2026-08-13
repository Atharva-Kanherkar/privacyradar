from __future__ import annotations

import pytest

from privacyradar.operator import OperatorError, validate_actor


def test_actor_rejects_email_and_url() -> None:
    with pytest.raises(OperatorError):
        validate_actor("user@example.test")
    with pytest.raises(OperatorError):
        validate_actor("https://example.test")
    with pytest.raises(OperatorError):
        validate_actor("CLI")
    assert validate_actor("cli:local") == "cli:local"
    assert validate_actor("ops_bot-1") == "ops_bot-1"
