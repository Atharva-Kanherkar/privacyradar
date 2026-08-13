import pytest

from privacyradar.cli import main


def test_cli_migrate_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["migrate", "--help"])
    assert exc.value.code == 0


def test_cli_unknown_command_exits_nonzero() -> None:
    try:
        main(["not-a-command"])
    except SystemExit as exc:
        assert exc.code != 0
        return
    raise AssertionError("expected argparse to reject an unknown command")
