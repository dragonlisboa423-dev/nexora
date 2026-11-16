import pytest
from fastapi.testclient import TestClient

from backend import main, security
from backend import storage as store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setenv("SALY_DATABASE_URL", "sqlite:///" + str(tmp_path / "saly-v2.sqlite3"))
    monkeypatch.setenv("SALY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SALY_OWNER_PASSWORD_HASH", "")
    monkeypatch.setenv("SALY_DISABLE_ALARM_SCHEDULER", "1")
    monkeypatch.setenv("SALY_DISABLE_BIOLOGY_SEED", "1")
    monkeypatch.setattr(main.provider, "key", "")
    from backend.agent.registry import integrations
    from backend.smolin.service import embedding_provider

    monkeypatch.setattr(integrations, "token", "")
    monkeypatch.setattr(integrations, "search_key", "")
    monkeypatch.setattr(integrations, "web_hosts", set())
    monkeypatch.setattr(embedding_provider, "url", "")
    security.ATTEMPTS.clear()
    with TestClient(main.app) as c:
        security.set_owner("test-private-owner-123")
        assert (
            c.post("/api/auth/login", json={"password": "test-private-owner-123"}).status_code
            == 200
        )
        yield c
