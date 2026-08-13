import subprocess
import sys
from pathlib import Path

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


def test_module_entrypoint_help() -> None:
    worker_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "privacyradar", "migrate", "--help"],
        cwd=worker_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "migrate" in completed.stdout
