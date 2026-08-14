import subprocess
import sys
from pathlib import Path

import pytest

from privacyradar.cli import main
from privacyradar.settings import settings


def test_cli_migrate_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["migrate", "--help"])
    assert exc.value.code == 0


def test_cli_eval_extract_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["eval-extract", "--help"])
    assert exc.value.code == 0


def test_cli_extract_observation_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["extract-observation", "--help"])
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


def test_cli_migrate_and_seed_fixtures(
    empty_database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "database_url", empty_database_url)
    assert main(["migrate"]) == 0
    assert "applied 0001" in capsys.readouterr().out
    assert main(["migrate"]) == 0
    assert "already at head" in capsys.readouterr().out
    assert main(["seed-fixtures"]) == 0
    first = capsys.readouterr().out
    assert "seeded 2 fixture companies" in first
    assert main(["seed-fixtures"]) == 0
    assert "seeded 0 fixture companies" in capsys.readouterr().out
    assert main(["reconcile-observations"]) == 0
    assert "observations_created=0" in capsys.readouterr().out
    assert main(["fetch-stats"]) == 0
    stats_out = capsys.readouterr().out
    assert "overdue_sources=" in stats_out
    assert "postgresql://" not in stats_out
    assert main(["eval-extract"]) == 0
    eval_out = capsys.readouterr().out
    assert "citation_validity=" in eval_out
    assert "n_fixtures=" in eval_out
    assert "postgresql://" not in eval_out
    assert "OPENAI" not in eval_out
    assert "placeholder and does not describe collection" not in eval_out
    assert main(["eval-materiality"]) == 0
    mat_out = capsys.readouterr().out
    assert "n_pairs=" in mat_out
    assert "postgresql://" not in mat_out
    assert main(["publish-stats"]) == 0
    pub_out = capsys.readouterr().out
    assert "review_pending=" in pub_out
    assert "postgresql://" not in pub_out


def test_cli_migrate_unavailable_database_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "database_url", "postgresql://127.0.0.1:1/none")
    assert main(["migrate"]) == 1
    err = capsys.readouterr().err
    assert "migrate failed" in err
    assert "postgresql://127.0.0.1:1/none" not in err


def test_cli_reconcile_unavailable_database_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "database_url", "postgresql://127.0.0.1:1/none")
    assert main(["reconcile-observations"]) == 1
    err = capsys.readouterr().err
    assert "reconcile-observations failed" in err
    assert "postgresql://127.0.0.1:1/none" not in err


def test_cli_seed_fixtures_unavailable_database_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "database_url", "postgresql://127.0.0.1:1/none")
    assert main(["seed-fixtures"]) == 1
    err = capsys.readouterr().err
    assert "seed-fixtures failed" in err
    assert "postgresql://" not in err


def test_cli_extract_observation_without_api_key_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert main(["extract-observation", "00000000-0000-0000-0000-000000000000"]) == 1
    err = capsys.readouterr().err
    assert "extract-observation failed" in err
    assert "sk-" not in err
    assert "OPENAI_API_KEY" not in err
