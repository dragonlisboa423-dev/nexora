import json
import os
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import main, storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA", tmp_path)
    storage.init()
    main.ATTEMPTS.clear()
    with TestClient(main.app) as c:
        assert (
            c.post(
                "/api/auth/register", json={"username": "owner", "password": "correct-password-123"}
            ).status_code
            == 200
        )
        yield c


def memory(client, **kwargs):
    r = client.post(
        "/api/memories",
        json={"content": "Meu projeto usa Python e FastAPI", "tags": ["projeto"], **kwargs},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_csrf_logout(client):
    assert client.get("/api/auth/me").status_code == 200
    assert (
        client.post(
            "/api/memories", json={"content": "x"}, headers={"origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/register", json={"username": "other", "password": "another-password-123"}
        ).status_code
        == 403
    )
    client.post("/api/auth/logout", json={})
    assert client.get("/api/memories").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"username": "owner", "password": "wrong-password-123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"username": "owner", "password": "correct-password-123"}
        ).status_code
        == 200
    )


def test_memory_crud_versions_search_delete(client):
    m = memory(client)
    assert client.get("/api/memories?q=Python").json()[0]["id"] == m["id"]
    changed = {**m, "content": "Corrigido: usa SQLite", "verification": "contested"}
    assert client.put("/api/memories/" + m["id"], json=changed).status_code == 200
    versions = client.get("/api/memories/" + m["id"] + "/versions").json()
    assert len(versions) == 1
    assert (
        client.post(f"/api/memories/{m['id']}/restore/{versions[0]['id']}", json={}).json()[
            "content"
        ]
        == m["content"]
    )
    assert len(client.get("/api/memories?q=Python").json()) == 1
    assert (
        client.post("/api/memories/delete", json={"ids": [m["id"]], "confirm": False}).status_code
        == 400
    )
    assert (
        client.post("/api/memories/delete", json={"ids": [m["id"]], "confirm": True}).json()[
            "deleted"
        ]
        == 1
    )
    assert not client.get("/api/memories").json()
    assert not client.get("/api/memories?q=Python").json()


def test_import_duplicates_relations(client):
    m = memory(client)
    n = memory(client, relations=[m["id"]])
    assert n["relations"] == [m["id"]]
    assert len(client.get("/api/memory-duplicates").json()) == 1
    exported = client.get("/api/memories-export").json()
    assert client.post("/api/memories-import", json=exported).json()["imported"] == 2
    assert all(m["verification"] == "unverified" for m in client.get("/api/memories").json())


def test_isolation(client):
    from backend.main import password_hash

    with storage.db() as db:
        db.execute(
            "INSERT INTO users VALUES(?,?,?)",
            ("second", "second", password_hash("second-password-123")),
        )
    m = memory(client)
    client.post("/api/auth/logout", json={})
    assert (
        client.post(
            "/api/auth/login", json={"username": "second", "password": "second-password-123"}
        ).status_code
        == 200
    )
    assert client.get("/api/memories?q=Python").json() == []
    assert client.put("/api/memories/" + m["id"], json={"content": "attack"}).status_code == 404
    assert client.get("/api/memories/" + m["id"] + "/versions").status_code == 404
    backup = client.post("/api/backup", json={}).json()
    assert backup["memories"] == []
    assert "users" not in backup and "sessions" not in backup


def test_documents_search_and_delete(client):
    r = client.post(
        "/api/knowledge",
        files={
            "file": ("nota.md", "O projeto Saly utiliza SQLite com busca textual.", "text/markdown")
        },
        headers={"x-saly-request": "1"},
    )
    assert r.status_code == 200, r.text
    results = client.get("/api/knowledge/search?q=SQLite").json()
    assert results[0]["name"] == "nota.md" and "SQLite" in results[0]["content"]
    assert (
        client.delete(
            "/api/knowledge/" + r.json()["id"], headers={"x-saly-request": "1"}
        ).status_code
        == 400
    )
    assert (
        client.delete(
            "/api/knowledge/" + r.json()["id"] + "?confirm=true", headers={"x-saly-request": "1"}
        ).status_code
        == 200
    )
    assert not client.get("/api/knowledge/search?q=SQLite").json()
    assert (
        client.post(
            "/api/knowledge", files={"file": ("x.exe", b"xx")}, headers={"x-saly-request": "1"}
        ).status_code
        == 422
    )


def test_evaluation_calculator_lists_settings(client):
    assert client.post("/api/tools/calculate", json={"expression": "2+3*4"}).json()["result"] == 14
    for expr in ["__import__('os').system('id')", "2**999999", "1/0", "[1]*999999999"]:
        assert client.post("/api/tools/calculate", json={"expression": expr}).status_code == 422
    tests = client.post("/api/evaluation", json={}).json()
    assert len(tests) == 8 and all(t["passed"] for t in tests)
    assert len(client.get("/api/evaluation").json()) == 1
    prefs = client.get("/api/settings").json()
    prefs["voice"]["rate"] = 1.3
    assert client.put("/api/settings", json=prefs).status_code == 200
    assert client.get("/api/settings").json()["voice"]["rate"] == 1.3
    task = client.post("/api/lists", json={"content": "revisar"}).json()
    client.put("/api/lists/" + task["id"], json={"content": "revisar", "done": True})
    assert client.get("/api/lists").json()[0]["done"] is True


def test_database_survives_restart(client):
    m = memory(client)
    env = {**os.environ, "SALY_DATA_DIR": str(storage.DATA)}
    code = "from backend.storage import db,init; init();\nwith db() as c: print(c.execute('SELECT content FROM memories').fetchone()[0])"
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, text=True, capture_output=True, check=True
    )
    assert m["content"] in result.stdout


def test_offline_never_simulates(client, monkeypatch):
    async def offline(owner):
        return {"model_ready": False, "detail": "Modelo offline"}

    monkeypatch.setattr(main, "health", offline)
    assert client.post("/api/chat", json={"message": "Olá"}).status_code == 503
    assert client.get("/api/conversations").json() == []


def test_stream_context_filters_and_persistence(client, monkeypatch):
    memory(client, content="Python preferência autorizada")
    memory(client, content="Python contestada", verification="contested")
    memory(client, content="Python arquivada", archived=True)
    memory(client, content="Python desativada", enabled=False)
    seen = {}

    class ModelClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return httpx.Response(
                200, json={"models": [{"name": main.MODEL}]}, request=httpx.Request("GET", url)
            )

        def stream(self, method, url, json):
            seen.update(json)
            return self

        def raise_for_status(self):
            pass

        async def aiter_lines(self):
            for e in [
                {"message": {"content": "Olá "}},
                {"message": {"content": "Saly"}, "done": True},
            ]:
                yield json.dumps(e)

    monkeypatch.setattr(main.httpx, "AsyncClient", ModelClient)
    response = client.post("/api/chat", json={"message": "Python"})
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert len(events[0]["memory_ids"]) == 1
    assert events[-1]["type"] == "done"
    assert "".join(e.get("text", "") for e in events) == "Olá Saly"
    history = client.get("/api/conversations/" + events[0]["conversation_id"]).json()
    assert history[-1]["content"] == "Olá Saly"
    assert "Python contestada" not in seen["messages"][0]["content"]
    # This tests the protocol with a controlled transport, not real model inference.


def test_rate_limit(client):
    for _ in range(10):
        client.post("/api/auth/login", json={"username": "owner", "password": "wrong-password-123"})
    assert (
        client.post(
            "/api/auth/login", json={"username": "owner", "password": "wrong-password-123"}
        ).status_code
        == 429
    )


@pytest.mark.parametrize(
    "route",
    [
        "/",
        "/memory",
        "/knowledge",
        "/voices",
        "/activity",
        "/evaluation",
        "/settings",
        "/settings/personality",
        "/settings/privacy",
        "/settings/system",
    ],
)
def test_built_routes(client, route):
    if not main.DIST.exists():
        pytest.skip("Frontend não compilado")
    response = client.get(route)
    assert response.status_code == 200
    assert "SALY Intelligence" in response.text


def test_consolidation_archives_originals_and_preserves_versions(client):
    a = memory(client, content="Projeto Python")
    b = memory(client, content="Projeto SQLite")
    body = {"ids": [a["id"], b["id"]], "content": "Projeto Python e SQLite", "confirm": False}
    assert client.post("/api/memories-consolidate", json=body).status_code == 400
    body["confirm"] = True
    merged = client.post("/api/memories-consolidate", json=body).json()
    assert merged["relations"] == body["ids"]
    records = client.get("/api/memories").json()
    assert len(records) == 3
    assert sum(r["archived"] for r in records) == 2
    assert len(client.get("/api/memories/" + a["id"] + "/versions").json()) == 1


def test_pdf_extracts_real_text(client):
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 200 Td (Saly SQLite documento) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buf = io.BytesIO()
    writer.write(buf)
    result = client.post(
        "/api/knowledge",
        files={"file": ("texto.pdf", buf.getvalue(), "application/pdf")},
        headers={"x-saly-request": "1"},
    )
    assert result.status_code == 200, result.text
    assert (
        "Saly SQLite documento" in client.get("/api/knowledge/search?q=SQLite").json()[0]["content"]
    )


def test_backup_restore_cli_preserves_data_and_invalidates_sessions(client, tmp_path):
    memory(client)
    snapshot = tmp_path / "backup.sqlite3"
    destination = tmp_path / "recovered"
    env = {**os.environ, "SALY_DATA_DIR": str(storage.DATA)}
    subprocess.run(
        [sys.executable, "-m", "backend.manage", "backup", str(snapshot)],
        env=env,
        check=True,
        capture_output=True,
    )
    restored = {**env, "SALY_DATA_DIR": str(destination)}
    subprocess.run(
        [sys.executable, "-m", "backend.manage", "restore", str(snapshot), "--confirm-stopped"],
        env=restored,
        check=True,
        capture_output=True,
    )
    import sqlite3

    with sqlite3.connect(destination / "saly.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM memories").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    result = subprocess.run(
        [sys.executable, "-m", "backend.manage", "restore", str(snapshot), "--confirm-stopped"],
        env=restored,
        check=False,
        capture_output=True,
    )
    assert result.returncode != 0


def test_voice_settings_validate_and_persist(client):
    prefs = client.get("/api/settings").json()
    prefs["voice"]["rate"] = 99
    assert client.put("/api/settings", json=prefs).status_code == 422
    prefs["voice"]["rate"] = 1.1
    prefs["voice"]["profiles"] = [
        {"name": "Pessoal", "voiceURI": "system-voice-id", "rate": 1.1, "pitch": 1, "volume": 0.8}
    ]
    assert client.put("/api/settings", json=prefs).status_code == 200
    assert client.get("/api/settings").json()["voice"]["profiles"][0]["name"] == "Pessoal"
