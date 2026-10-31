"""Installer regression: never compile pydantic-core under an unintended Python."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PREPARE = Path(__file__).resolve().parents[2] / "scripts" / "prepare-python.sh"


def run_prepare(root, **extra):
    return subprocess.run(
        ["bash", "-c", 'source "$1"; saly_prepare_python "$2"', "_", str(PREPARE), str(root)],
        env={**os.environ, "SALY_PYTHON": sys.executable, "PIP_NO_INDEX": "true", **extra},
        text=True,
        capture_output=True,
        check=False,
    )


def test_installer_preserves_broken_environment_and_reuses_python312(tmp_path):
    if sys.version_info[:2] != (3, 12):
        pytest.skip("Project installer targets Python 3.12")
    broken = tmp_path / ".venv"
    (broken / "bin").mkdir(parents=True)
    (broken / "marker").write_text("preserve this dependency environment")
    (broken / "bin" / "python").write_text("#!/bin/sh\nexit 1\n")
    (broken / "bin" / "python").chmod(0o755)
    (tmp_path / ".env").write_text("PRIVATE_CONFIG=preserve\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "sentinel").write_text("persistent data")
    first = run_prepare(tmp_path)
    assert first.returncode == 0, first.stderr
    backups = list(tmp_path.glob(".venv.previous.*"))
    assert len(backups) == 1 and (backups[0] / "marker").exists()
    check = subprocess.run(
        [str(tmp_path / ".venv/bin/python"), "-c", "import sys; print(sys.version_info[:2])"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "(3, 12)" in check.stdout
    second = run_prepare(tmp_path)
    assert second.returncode == 0, second.stderr
    assert len(list(tmp_path.glob(".venv.previous.*"))) == 1
    assert (tmp_path / ".env").read_text() == "PRIVATE_CONFIG=preserve\n"
    assert (tmp_path / "data/sentinel").read_text() == "persistent data"


def test_installer_rejects_explicit_wrong_python_without_touching_files(tmp_path):
    wrong = tmp_path / "python-wrong"
    wrong.write_text("#!/bin/sh\nexit 1\n")
    wrong.chmod(0o755)
    result = run_prepare(tmp_path, SALY_PYTHON=str(wrong))
    assert result.returncode != 0
    assert "SALY requer Python 3.12" in result.stderr
    assert not (tmp_path / ".venv").exists()
