"""Disposable authenticated local app for browser suites; all external credentials disabled."""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "disposable-saly-browser-password-123"


@contextmanager
def test_server(port=8003, extra_environment=None):
    with tempfile.TemporaryDirectory(prefix="saly-browser-") as directory:
        environment = {
            **os.environ,
            "SALY_DATA_DIR": directory,
            "SALY_DATABASE_URL": "sqlite:///" + directory + "/saly-v2.sqlite3",
            "SALY_LLM_API_KEY": "",
            "GROQ_API_KEY": "",
            "SALY_OWNER_PASSWORD_HASH": "",
            "SALY_SECURE_COOKIE": "0",
            "SALY_EMBEDDING_URL": "",
            "SALY_GITHUB_TOKEN": "",
            "SALY_SEARCH_API_KEY": "",
            **(extra_environment or {}),
        }
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from backend import storage; from backend.security import set_owner; storage.initialize(); set_owner('"
                + PASSWORD
                + "')",
            ],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            for _ in range(100):
                try:
                    urllib.request.urlopen(url + "/api/bootstrap", timeout=1)
                    break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError("Servidor de teste encerrou antes de iniciar") from None
                    time.sleep(0.1)
            else:
                raise RuntimeError("Servidor de teste não iniciou")
            yield url
        finally:
            server.terminate()
            server.wait(timeout=10)
