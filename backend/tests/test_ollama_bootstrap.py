"""Bootstrap process/files regression; controlled executable, no network/models/downloads."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/start-ollama.sh"


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path / "app"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(SCRIPT, root / "scripts/start-ollama.sh")
    mockbin = root / "mock-bin"
    mockbin.mkdir()
    curl = mockbin / "curl"
    curl.write_text('#!/bin/sh\ntest -f "$TEST_RUNTIME/models/ready"\n')
    curl.chmod(0o755)
    binary = mockbin / "ollama"
    binary.write_text(f"""#!{sys.executable}
import os, stat
from pathlib import Path
models=Path(os.environ["OLLAMA_MODELS"])
log=models.parent / "server.log"
assert log.is_file()
assert stat.S_IMODE(log.stat().st_mode) == 0o600
assert "SALY_LLM_API_KEY" not in os.environ
assert os.environ["OLLAMA_HOST"] == "127.0.0.1:11434"
print("CONTROLLED_RUNTIME_STARTED", flush=True)
(models / "ready").write_text("ready")
""")
    binary.chmod(0o755)
    return root, {
        **os.environ,
        "PATH": str(mockbin) + os.pathsep + os.defpath,
        "TEST_RUNTIME": str(root / ".tools/ollama"),
        "SALY_LLM_API_KEY": "test-canary-never-pass-to-runtime",
    }


def start(root, env):
    return subprocess.run(
        ["bash", "-c", 'umask 000; bash "$1"', "_", str(root / "scripts/start-ollama.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


@pytest.mark.parametrize("existing_log", [False, True])
def test_bootstrap_private_files_preserves_logs_and_reuses_ready_server(runtime, existing_log):
    root, env = runtime
    directory = root / ".tools/ollama"
    log = directory / "server.log"
    if existing_log:
        directory.mkdir(parents=True)
        log.write_text("PRESERVE_PREVIOUS_DIAGNOSTIC\n")
        log.chmod(0o644)
    first = start(root, env)
    assert first.returncode == 0, first.stdout + first.stderr
    assert "Ollama iniciado" in first.stdout
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    assert stat.S_IMODE((directory / "server.pid").stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    output = log.read_text()
    assert output.count("CONTROLLED_RUNTIME_STARTED") == 1
    if existing_log:
        assert output.startswith("PRESERVE_PREVIOUS_DIAGNOSTIC\n")
    assert env["SALY_LLM_API_KEY"] not in output
    # Readiness short-circuits a second launch and leaves the original PID/log intact.
    pid = (directory / "server.pid").read_text()
    second = start(root, env)
    assert second.returncode == 0 and "já responde" in second.stdout
    assert log.read_text() == output
    assert (directory / "server.pid").read_text() == pid
