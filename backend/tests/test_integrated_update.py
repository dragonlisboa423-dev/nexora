import asyncio
import io
import json
import stat
import zipfile

import httpx
import pytest
from sqlalchemy import select
from test_smolin_files import finished, package, send

from backend import main
from backend import storage as store
from backend.llm import ollama
from backend.llm.provider import ProviderError
from backend.smolin import service
from backend.smolin.archives import extract_archive


def test_zip_nested_content_sources_preview_and_cascade(client):
    raw = package(
        {
            "ciencia/notas.txt": "Fotossíntese produz oxigênio e açúcares.",
            "ciencia/dados.json": '{"estudo":"clorofila"}',
            "ciencia/pagina.html": "<h1>Botânica</h1><script>alert(1)</script>",
            "codigo/start.sh": "touch /tmp/never-execute-upload",
            "outro.bin": b"\x00\xff",
        }
    )
    doc = finished(client, send(client, raw, "colecao.zip")["id"])
    assert doc["status"] == "partial", doc
    entries = doc["archive_entries"]
    assert entries[0]["status"] == "ready"
    assert entries[3]["status"] == "blocked" and entries[4]["status"] == "unsupported"
    assert "alert(1)" not in doc["content"] and "touch" not in doc["content"]
    sources = asyncio.run(service.search("Fotossíntese", remote_allowed=False))
    assert sources[0]["archive_path"] == "ciencia/notas.txt"
    assert sources[0]["source_page"] == 1 and "/entries/0/original#page=1" in sources[0]["url"]
    root = "/api/knowledge/" + doc["id"]
    assert (
        client.get(root + "/entries/0/original").content
        == "Fotossíntese produz oxigênio e açúcares.".encode()
    )
    assert (
        client.get(root + "/entries/2/original")
        .headers["content-disposition"]
        .startswith("attachment;")
    )
    assert client.get(root + "/entries/3/original").status_code == 422
    assert client.get(root + "/original").content == raw
    assert not store.all_records("memories")
    assert client.delete(root + "?confirm=true", headers={"X-Saly-Request": "1"}).status_code == 200
    assert client.get(root + "/entries/0/original").status_code == 404
    with store.db() as c:
        assert not c.execute(
            select(store.chunks).where(store.chunks.c.document_id == doc["id"])
        ).first()


@pytest.mark.parametrize(
    "name", ["../escape.txt", "/etc/a.txt", "C:/a.txt", "a\\b.txt", "a/./b.txt", "a/../../b.txt"]
)
def test_zip_rejects_paths_before_reading(tmp_path, name):
    path = tmp_path / "bad.zip"
    path.write_bytes(package({name: "secret"}))
    with pytest.raises(ValueError, match="caminho"):
        extract_archive(path, 100)


def test_zip_symlink_bomb_duplicates_and_count(tmp_path, monkeypatch):
    path = tmp_path / "bad.zip"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "/etc/passwd")
    path.write_bytes(out.getvalue())
    with pytest.raises(ValueError, match="link"):
        extract_archive(path, 100)
    path.write_bytes(package({"bomb.txt": "0" * 200000}))
    with pytest.raises(ValueError, match="compressão"):
        extract_archive(path, 100)
    path.write_bytes(package({"A.txt": "a", "a.txt": "b"}))
    with pytest.raises(ValueError, match="duplicados"):
        extract_archive(path, 100)
    path.write_bytes(package({"a": "texto", "a/b.txt": "texto"}))
    with pytest.raises(ValueError, match="conflito"):
        extract_archive(path, 100)
    monkeypatch.setenv("SALY_ZIP_MAX_ENTRIES", "1")
    with pytest.raises(ValueError, match="quantidade"):
        extract_archive(path, 100)


def mock_ollama(monkeypatch, handler):
    monkeypatch.setattr(
        ollama,
        "client",
        lambda: httpx.AsyncClient(base_url=ollama.BASE, transport=httpx.MockTransport(handler)),
    )


def test_local_native_stream_release_and_catalog_truth(client, monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.url.path, json.loads(request.content) if request.content else {}))
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": "qwen2.5:3b", "digest": "sha-test", "size": 2500}]},
            )
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"done": True})
        return httpx.Response(200, content=b'{"message":{"content":"Quatro."},"done":true}\n')

    mock_ollama(monkeypatch, handler)
    catalog = client.get("/api/local-models").json()
    assert catalog["models"][0]["status"] == "installed_unverified"
    assert catalog["models"][2]["status"] == "not_installed"
    probe = client.post("/api/local-models/probe", json={"model": "qwen2.5:3b"})
    assert probe.status_code == 200 and probe.json()["response"] == "Quatro."
    assert not probe.json()["capabilities"]["tools_verified"]
    assert client.get("/api/local-models").json()["models"][0]["status"] == "ready"
    chat = next(body for path, body in seen if path == "/api/chat")
    assert chat["keep_alive"] == 300
    assert not any(path == "/api/generate" for path, _ in seen)
    assert "tools" not in chat


def test_switch_same_conversation_keeps_history_and_actual_reply_model(client, monkeypatch):
    turns = []

    async def capabilities(self):
        return {"declared": ["completion"]}

    async def stream(self, messages, tools=None):
        turns.append(messages)
        assert tools is None
        yield {"text": "Resposta em português de " + self.model}
        yield {"done": True}

    monkeypatch.setattr(ollama.Ollama, "capabilities", capabilities)
    monkeypatch.setattr(ollama.Ollama, "stream", stream)
    assert client.put("/api/local-models/selection", json={"model": "qwen2.5:3b"}).status_code == 200
    # Consent remains false; local inference does not send to remote embeddings/providers.
    assert not main.settings(True)["privacy"]["remoteConsent"]
    first = client.post("/api/chat", json={"message": "Primeira pergunta."})
    events = [json.loads(line) for line in first.text.splitlines()]
    cid = events[0]["conversation_id"]
    assert events[-1]["model"] == "qwen2.5:3b"
    assert (
        client.put(
            "/api/local-models/selection", json={"model": "gemma3:4b", "conversation_id": cid}
        ).status_code
        == 200
    )
    second = client.post("/api/chat", json={"message": "Segunda pergunta.", "conversation_id": cid})
    assert json.loads(second.text.splitlines()[-1])["model"] == "gemma3:4b"
    assert any(m["content"] == "Primeira pergunta." for m in turns[-1])
    records = main.messages(cid, True)
    assert [m["model"] for m in records if m["role"] == "assistant"] == ["qwen2.5:3b", "gemma3:4b"]
    assert (
        client.put("/api/local-models/selection", json={"model": "arbitrary-host"}).status_code
        == 422
    )


def test_local_missing_server_no_fallback(client, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("offline")

    mock_ollama(monkeypatch, handler)
    assert client.get("/api/local-models").json()["server"] == "server_offline"
    assert client.post("/api/local-models/probe", json={"model": "granite4:3b"}).status_code == 503
    with pytest.raises(ProviderError):
        asyncio.run(ollama.Ollama("gemma3:4b").capabilities())


def test_zip_pdf_docx_corrupt_member_and_limits(client, tmp_path, monkeypatch):
    from test_api import pdf_bytes

    raw = package(
        {
            "livros/original.pdf": pdf_bytes(
                ["Fotossintese no cloroplasto.", "Clorofila na folha."]
            ),
            "notas/resumo.docx": package(
                {"word/document.xml": "<document><p><t>ATP e energia</t></p></document>"}
            ),
            "notas/quebrado.pdf": b"%PDF-invalido",
            "vazia/": "",
        }
    )
    doc = finished(client, send(client, raw, "livros.zip")["id"])
    assert doc["status"] == "partial"
    assert [e["status"] for e in doc["archive_entries"]] == ["ready", "ready", "error", "directory"]
    second = next(
        p
        for p in doc["pages"]
        if p["archive_path"].endswith("original.pdf") and p["source_page"] == 2
    )
    assert "Clorofila" in second["content"]
    original = client.get(f"/api/knowledge/{doc['id']}/entries/0/original")
    assert (
        original.content.startswith(b"%PDF-")
        and original.headers["content-type"] == "application/pdf"
    )
    path = tmp_path / "large.zip"
    path.write_bytes(raw)
    monkeypatch.setenv("SALY_ZIP_MAX_DEPTH", "1")
    with pytest.raises(ValueError, match="profundidade"):
        extract_archive(path, 100)


def test_zip_encryption_flag_and_expansion_budget(tmp_path, monkeypatch):
    import struct

    # Mark both central and local headers as encrypted; no password is ever requested.
    raw = bytearray(package({"note.txt": "texto privado"}))
    local = raw.find(b"PK\x03\x04")
    central = raw.find(b"PK\x01\x02")
    struct.pack_into("<H", raw, local + 6, 1)
    struct.pack_into("<H", raw, central + 8, 1)
    path = tmp_path / "encrypted.zip"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="criptografado"):
        extract_archive(path, 100)
    monkeypatch.setenv("SALY_ZIP_MAX_EXPANDED_MB", "1")
    # Incompressible data makes the expanded-size gate independent from ratio protection.
    import os

    path.write_bytes(package({"large.bin": os.urandom(1100000)}))
    with pytest.raises(ValueError, match="expandido"):
        extract_archive(path, 100)


def test_zip_directory_preflight_before_allocation(tmp_path):
    import struct

    raw = bytearray(package({"safe.txt": "texto"}))
    central = raw.rfind(b"PK\x05\x06")
    struct.pack_into("<H", raw, central + 8, 3000)
    struct.pack_into("<H", raw, central + 10, 3000)
    path = tmp_path / "too-many.zip"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="quantidade"):
        extract_archive(path, 100)


def test_zip_actual_image_ocr(client):
    import shutil

    if not shutil.which("tesseract"):
        pytest.skip("Motor OCR nativo ausente")
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (700, 180), "white")
    ImageDraw.Draw(image).text(
        (25, 50), "BIOLOGY PLANTS", font=ImageFont.truetype("DejaVuSans.ttf", 48), fill="black"
    )
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    doc = finished(
        client,
        send(client, package({"imagens/pagina.png": payload.getvalue()}), "imagens.zip")["id"],
    )
    assert doc["archive_entries"][0]["status"] == "ready", doc
    assert "BIOLOGY" in doc["content"].upper()
    assert doc["pages"][0]["archive_path"] == "imagens/pagina.png"


def test_zip_derived_storage_quota_keeps_original(client, monkeypatch):
    import random

    rng = random.Random(42)
    text = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz ", k=200000))
    monkeypatch.setenv("SALY_MAX_TOTAL_MB", "1")
    raw = package({"notas/large.txt": text})
    doc = finished(client, send(client, raw, "quota.zip")["id"])
    assert doc["status"] == "failed"
    assert not doc["chunks"]
    assert client.get("/api/knowledge/" + doc["id"] + "/original").content == raw
