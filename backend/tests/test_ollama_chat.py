"""Local chat eligibility vs proven generation, using an explicit controlled HTTP transport."""

import asyncio
import json

import httpx
import pytest

from backend import main
from backend import storage as store
from backend.llm import ollama


@pytest.fixture
def native(client, monkeypatch):
    store.set_setting("llm_default", "granite4:3b")
    state = {
        "digest": "d1",
        "body": b'{"message":{"content":"Resposta controlada."},"done":true}\n',
        "status": 200,
        "calls": [],
    }

    def handler(request):
        state["calls"].append(request.url.path)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": "granite4:3b", "digest": state["digest"], "size": 1}]},
            )
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion"]})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"done": True})
        assert request.url.path == "/api/chat"
        if state.get("timeout"):
            raise httpx.ReadTimeout("controlled read timeout")
        return httpx.Response(state["status"], content=state["body"])

    monkeypatch.setattr(
        ollama,
        "client",
        lambda: httpx.AsyncClient(base_url=ollama.BASE, transport=httpx.MockTransport(handler)),
    )
    return state


def events(response):
    assert response.status_code == 200, response.text
    return [json.loads(line) for line in response.text.splitlines()]


def test_first_installed_message_allowed_and_proves_generation(client, native):
    choice = client.get("/api/local-models").json()
    assert choice["selected"] == "granite4:3b" and not choice["remote_configured"]
    before = client.get("/api/health").json()
    assert before["can_chat"] and not before["model_ready"]
    assert "/api/chat" not in native["calls"]  # Inventory/health never generate.
    result = events(client.post("/api/chat", json={"message": "Uma mensagem privada."}))
    assert result[-1]["type"] == "done" and result[-1]["model"] == "granite4:3b"
    after = client.get("/api/health").json()
    assert after["can_chat"] and after["model_ready"]
    proof = store.setting("ollama_probe:granite4:3b")
    assert proof["digest"] == "d1" and proof["ok"]
    assert "response" not in proof and "Resposta controlada" not in str(proof)
    assert "Uma mensagem privada" not in str(proof)
    assert not main.settings(True)["privacy"]["remoteConsent"]
    assert native["calls"].count("/api/chat") == 1
    assert "/api/generate" not in native["calls"]


def test_explicit_remote_choice_and_configured_remote_never_autoswitch(client, native, monkeypatch):
    store.set_setting("llm_default", "remote")
    monkeypatch.setattr(main.provider, "key", "controlled-test-key")
    assert client.get("/api/local-models").json()["selected"] == "remote"
    monkeypatch.setattr(main.provider, "key", "")
    client.put("/api/local-models/selection", json={"model": "remote"})
    assert client.get("/api/local-models").json()["selected"] == "remote"
    assert not client.get("/api/health").json()["model_ready"]
    assert client.post("/api/chat", json={"message": "Não enviar ao remoto."}).status_code == 412
    assert "/api/chat" not in native["calls"]


@pytest.mark.parametrize(
    "body", [b'{"message":{"content":""},"done":true}\n', b'{"message":{"content":"Parcial"}}\n']
)
def test_empty_or_truncated_does_not_save_reply_or_certify(client, native, body):
    native["body"] = body
    result = events(client.post("/api/chat", json={"message": "Teste sem resposta completa."}))
    assert result[-1]["type"] == "error"
    assert not client.get("/api/health").json()["model_ready"]
    assert not store.setting("ollama_probe:granite4:3b")["ok"]
    assert all(m["role"] != "assistant" for m in store.all_records("messages"))
    assert native["calls"].count("/api/chat") == 1


def test_memory_error_is_visible_and_no_auto_retry(client, native):
    native["status"] = 500
    native["body"] = b'{"error":"requires more system memory"}'
    result = events(client.post("/api/chat", json={"message": "Teste de falta de memória."}))
    assert result[-1]["type"] == "error" and "Memória insuficiente" in result[-1]["detail"]
    health = client.get("/api/health").json()
    assert health["reason"] == "resource_error" and not health["model_ready"]
    assert health["can_chat"]  # An explicit later retry remains possible; no background retry.
    assert native["calls"].count("/api/chat") == 1
    assert all(m["role"] != "assistant" for m in store.all_records("messages"))


def test_changed_digest_requires_new_generation(client, native):
    result = client.post("/api/local-models/probe", json={"model": "granite4:3b"})
    assert result.status_code == 200 and result.json()["response"] == "Resposta controlada."
    native["digest"] = "d2"
    health = client.get("/api/health").json()
    assert health["can_chat"] and not health["model_ready"]
    assert health["reason"] == "installed_unverified"


def test_cancelled_stream_never_certifies(client, native):
    native["body"] = b'{"message":{"content":"Parcial privado"}}\n'

    async def cancel():
        stream = ollama.Ollama("granite4:3b").stream([{"role": "user", "content": "Teste"}])
        assert await anext(stream) == {"text": "Parcial privado"}
        await stream.aclose()

    asyncio.run(cancel())
    assert not store.setting("ollama_probe:granite4:3b", {}).get("ok")
    assert native["calls"][-1] == "/api/generate"


def test_local_timeout_delivers_error_inside_stream(client, native):
    native["timeout"] = True
    result = events(client.post("/api/chat", json={"message": "Teste de espera excedida."}))
    assert result[-1]["type"] == "error"
    assert "tempo de espera" in result[-1]["detail"]
    assert not any(item["type"] == "done" for item in result)
    assert all(item["role"] != "assistant" for item in store.all_records("messages"))
    assert not store.setting("ollama_probe:granite4:3b")["ok"]
    assert native["calls"].count("/api/chat") == 1


def test_total_response_deadline_ends_with_error_not_broken_http(client, native, monkeypatch):
    closed = []

    async def slow(self, messages, tools=None):
        try:
            await asyncio.sleep(0.15)
            yield {"text": "late"}
        finally:
            closed.append(True)

    monkeypatch.setattr(ollama.Ollama, "stream", slow)
    monkeypatch.setattr(main, "LOCAL_CHAT_TIMEOUT_SECONDS", 0.05)
    result = events(client.post("/api/chat", json={"message": "Teste de prazo total."}))
    assert result[-1]["type"] == "error"
    assert "tempo máximo" in result[-1]["detail"]
    assert closed == [True]
    assert all(item["role"] != "assistant" for item in store.all_records("messages"))
