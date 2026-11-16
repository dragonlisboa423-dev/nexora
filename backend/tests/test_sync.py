import json
import uuid

from sqlalchemy import select

from backend import storage as store
from backend import sync


def operation(kind="memories", key=None, revision=0, action="upsert", **changes):
    return {
        "id": str(uuid.uuid4()),
        "entity_type": kind,
        "entity_id": key or uuid.uuid4().hex,
        "action": action,
        "base_revision": revision,
        "payload": {"content": "Rascunho autorizado"} if kind == "memories" else {},
        **changes,
    }


def push(client, value):
    response = client.post("/api/sync/push", json={"operations": [value]})
    assert response.status_code == 200, response.text
    return response.json()["results"][0]


def test_sync_bootstrap_revision_write_retry_and_private_receipt(client):
    assert client.get("/api/sync/bootstrap").json()["schema_version"] == 1
    value = operation(payload={"content": "PRIVATE_SYNC_SENTINEL"})
    result = push(client, value)
    assert result["status"] == "applied" and result["record"]["revision"] == 1
    repeated = push(client, value)
    assert repeated["duplicate"] and repeated["record"]["revision"] == 1
    assert len(store.all_records("memories")) == 1
    with store.db() as connection:
        receipts = [dict(row) for row in connection.execute(select(store.sync_receipts)).mappings()]
    assert "PRIVATE_SYNC_SENTINEL" not in json.dumps(receipts)
    assert (
        push(client, {**value, "payload": {"content": "Different payload"}})["status"] == "invalid"
    )
    assert store.get("memories", value["entity_id"])["content"] == "PRIVATE_SYNC_SENTINEL"


def test_sync_detects_other_device_edit_and_propagates_delete_without_resurrection(client):
    first = operation()
    saved = push(client, first)["record"]
    bootstrap_cursor = client.get("/api/sync/bootstrap").json()["cursor"]
    client.put("/api/memories/" + saved["id"], json={"content": "Edição por outro dispositivo"})
    stale = operation(
        key=saved["id"], revision=saved["revision"], payload={"content": "Rascunho offline"}
    )
    conflict = push(client, stale)
    assert conflict["status"] == "conflict" and conflict["record"]["revision"] == 2
    assert conflict["record"]["content"] == "Edição por outro dispositivo"
    deletion = operation(key=saved["id"], revision=2, action="delete", payload={}, confirmed=True)
    assert push(client, deletion)["deleted"]
    changes = client.get(f"/api/sync/pull?after={bootstrap_cursor}").json()["changes"]
    assert any(
        item["entity_id"] == saved["id"] and item["deleted"] and item["record"] is None
        for item in changes
    )
    assert push(client, operation(key=saved["id"], revision=3))["status"] == "conflict"
    assert store.get("memories", saved["id"]) is None
    assert push(client, deletion)["duplicate"]


def test_sync_operation_rolls_back_domain_log_and_receipt_together(client, monkeypatch):
    real_save = sync.memory_save
    before = client.get("/api/sync/bootstrap").json()["cursor"]

    def fail_after_write(*args, **kwargs):
        real_save(*args, **kwargs)
        raise ValueError("Injected transaction failure")

    monkeypatch.setattr(sync, "memory_save", fail_after_write)
    value = operation()
    assert push(client, value)["status"] == "invalid"
    assert store.get("memories", value["entity_id"]) is None
    assert client.get("/api/sync/bootstrap").json()["cursor"] == before
    with store.db() as connection:
        assert connection.execute(select(store.sync_receipts)).first() is None


def test_sync_validates_confirmation_target_and_reminder_timezone(client):
    value = operation()
    saved = push(client, value)["record"]
    assert (
        push(client, operation(key=saved["id"], revision=1, action="delete", payload={}))["status"]
        == "invalid"
    )
    reminder = operation(
        kind="reminders",
        confirmed=True,
        payload={"title": "Estudar", "due_at": "2026-11-17T13:00", "timezone": "America/Sao_Paulo"},
    )
    result = push(client, reminder)
    assert result["status"] == "applied" and result["record"]["due_at"].startswith(
        "2026-11-17T16:00"
    )
    assert (
        push(client, operation(kind="reminders", payload=reminder["payload"]))["status"]
        == "invalid"
    )
    # A memory relation failure cannot partially install an invalid record.
    assert (
        push(client, operation(payload={"content": "Invalid relation", "relations": ["missing"]}))[
            "status"
        ]
        == "invalid"
    )


def test_sync_rejects_unknown_tools_unauthorized_access_and_restored_cursor(client):
    assert (
        client.post(
            "/api/sync/push", json={"operations": [operation(kind="tool_executions")]}
        ).status_code
        == 422
    )
    assert client.get("/api/sync/pull?after=999999").status_code == 409
    client.cookies.clear()
    assert client.get("/api/sync/bootstrap").status_code == 401
    assert client.post("/api/sync/push", json={"operations": [operation()]}).status_code == 401
