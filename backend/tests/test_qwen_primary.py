"""Qwen preference migration and warm streaming, not a claim of installed model weights."""

import asyncio
import json

import httpx

from backend import storage as store
from backend.llm import ollama


def test_primary_migration_once_preserves_data_and_retired_reply_labels(client):
    store.set_setting("qwen_primary_v1", {})
    store.set_setting("llm_default", "phi4-mini")
    conversation = store.save("conversations", {"title": "Preservar", "llm_choice": "phi4-mini"})
    reply = store.save(
        "messages",
        {
            "conversation_id": conversation["id"],
            "role": "assistant",
            "model": "phi4-mini",
            "content": "Resposta histórica",
        },
    )
    ollama.configure_primary()
    assert store.setting("llm_default") == "qwen2.5:3b"
    assert store.setting("qwen_primary_v1")["previous_default"] == "phi4-mini"
    assert asyncio.run(ollama.resolve_selection(conversation)) == "qwen2.5:3b"
    assert store.get("messages", reply["id"])["model"] == "phi4-mini"
    assert client.put("/api/local-models/selection", json={"model": "phi4-mini"}).status_code == 422
    client.put("/api/local-models/selection", json={"model": "gemma3:4b"})
    ollama.configure_primary()
    assert store.setting("llm_default") == "gemma3:4b"  # Never override later manual choices.


def test_warm_stream_timing_and_no_phi_in_chat_catalog(client, monkeypatch):
    calls = []

    def handle(request):
        payload = json.loads(request.content) if request.content else {}
        calls.append((request.url.path, payload))
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": name, "digest": name + "-digest", "size": 1}
                        for name in ("qwen2.5:3b", "phi4-mini:latest", "gemma3:4b")
                    ]
                },
            )
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion"]})
        assert request.url.path == "/api/chat"  # Successful same-model reuse must not unload.
        return httpx.Response(
            200,
            content=b'{"message":{"content":"H2O"}}\n{"done":true,"load_duration":1234,"eval_count":1}\n',
        )

    monkeypatch.setattr(
        ollama,
        "client",
        lambda: httpx.AsyncClient(base_url=ollama.BASE, transport=httpx.MockTransport(handle)),
    )
    store.set_setting("llm_default", ollama.PRIMARY)
    for _ in range(2):
        result = client.post("/api/local-models/probe", json={"model": ollama.PRIMARY})
        assert result.status_code == 200, result.text
        proof = result.json()
        assert (
            proof["first_token_seconds"] >= 0
            and proof["first_token_seconds"] <= proof["seconds"] + 0.01
        )
        assert proof["runtime_metrics"]["load_duration"] == 1234
    chat_calls = [body for path, body in calls if path == "/api/chat"]
    assert len(chat_calls) == 2 and all(body["keep_alive"] == 300 for body in chat_calls)
    inventory = client.get("/api/local-models").json()
    assert inventory["selected"] == "qwen2.5:3b"
    assert "phi4-mini" not in [item["id"] for item in inventory["models"]]
    health = client.get("/api/health").json()
    assert health["runtime"]["endpoint"] == "http://127.0.0.1:11434"
    assert health["runtime"]["hostname"]
