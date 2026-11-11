from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete

from . import storage as store


class Memory(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    category: str = Field(default="informacoes", max_length=60)
    tags: list[str] = Field(default_factory=list, max_length=50)
    source: str = Field(default="manual", max_length=300)
    verification: str = Field(default="unverified", pattern="^(unverified|verified|contested)$")
    archived: bool = False
    enabled: bool = True
    importance: float = Field(default=0.5, ge=0, le=1)
    expires_at: str | None = None
    relations: list[str] = Field(default_factory=list, max_length=100)


def memory_save(body, key=None):
    for relation in body.relations:
        if not store.get("memories", relation):
            raise HTTPException(422, "Relação não encontrada")
    if key:
        current = store.get("memories", key)
        if not current:
            raise HTTPException(404, "Memória não encontrada")
        store.save("versions", {"memory_id": key, "snapshot": current})
        store.set_setting("context_epoch", store.setting("context_epoch", 0) + 1)
        with store.db() as connection:
            connection.execute(delete(store.memory_vectors).where(store.memory_vectors.c.id == key))
    result = store.save("memories", body.model_dump(), key)
    store.audit("memory", "Memória registrada: " + result["id"])
    return result


def memory_delete(key):
    if not store.get("memories", key):
        raise HTTPException(404, "Memória não encontrada")
    store.remove("memories", key)
    for version in store.all_records("versions"):
        if version["memory_id"] == key:
            store.remove("versions", version["id"])
    for message in store.all_records("messages"):
        if key in message.get("memory_ids", []):
            store.save(
                "messages",
                {
                    **message,
                    "content": "[Resposta derivada de memória excluída removida.]",
                    "memory_ids": [],
                },
                message["id"],
            )
    for m in store.all_records("memories"):
        if key in m.get("relations", []):
            store.save(
                "memories", {**m, "relations": [r for r in m["relations"] if r != key]}, m["id"]
            )
    store.set_setting("context_epoch", store.setting("context_epoch", 0) + 1)
    for approval in store.all_records("agent_approvals"):
        if approval["status"] == "pending":
            store.save("agent_approvals", {**approval, "status": "expired"}, approval["id"])
    store.audit("memory", "Memória e representações derivadas excluídas: " + key)
