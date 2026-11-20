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


def start_fixture(tmp_path):
    import shutil
    import time

    root = tmp_path / "app"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(PREPARE.parent / "start.sh", root / "scripts/start.sh")
    (root / ".venv/bin").mkdir(parents=True)
    (root / ".venv/bin/python").symlink_to(sys.executable)
    (root / "frontend/src").mkdir(parents=True)
    (root / "frontend/dist").mkdir(parents=True)
    (root / "frontend/src/main.tsx").write_text("new selector source")
    index = root / "frontend/dist/index.html"
    index.write_text("old interface")
    os.utime(index, (time.time() - 100, time.time() - 100))
    (root / "backend").mkdir()
    (root / "backend/__init__.py").write_text("")
    (root / "backend/serve.py").write_text("print('BACKEND_STARTED')")
    (root / "mock-bin").mkdir()
    npm = root / "mock-bin/npm"
    npm.write_text(
        "#!/bin/sh\n[ \"${FAIL_BUILD:-0}\" = 1 ] && exit 7\nprintf 'build\\n' >> build-events\nprintf 'new interface' > frontend/dist/index.html\n"
    )
    npm.chmod(0o755)
    (root / ".env").write_text("PRIVATE=preserve")
    return root


def test_start_rebuilds_stale_interface_once_before_starting_backend(tmp_path):
    root = start_fixture(tmp_path)
    env = {**os.environ, "PATH": str(root / "mock-bin") + os.pathsep + os.defpath}
    for _ in range(2):
        result = subprocess.run(
            ["bash", str(root / "scripts/start.sh")],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "BACKEND_STARTED" in result.stdout
    assert (root / "build-events").read_text() == "build\n"
    assert (root / "frontend/dist/index.html").read_text() == "new interface"
    assert (root / ".env").read_text() == "PRIVATE=preserve"


def test_start_does_not_serve_stale_interface_after_failed_build(tmp_path):
    root = start_fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(root / "scripts/start.sh")],
        check=False,
        env={
            **os.environ,
            "PATH": str(root / "mock-bin") + os.pathsep + os.defpath,
            "FAIL_BUILD": "1",
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 7
    assert "BACKEND_STARTED" not in result.stdout
    assert (root / "frontend/dist/index.html").read_text() == "old interface"
