"""Authenticated revision sync. No external actions and no personal payload in receipts."""

import hashlib
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, insert, select

from . import storage as store
from .agent.registry import Reminder, completed_reminder
from .security import owner, throttle
from .services import Memory, memory_delete, memory_save

router = APIRouter(prefix="/api/sync", tags=["private-sync"])
WRITABLE = {"memories", "reminders"}


def safe_record(kind, record):
    if record is None:
        return None
    record = {**record, "revision": int(record.get("revision", 1))}
    if kind == "documents":
        return {key: value for key, value in record.items() if key not in ("content", "pages")}
    return record


def cursor(connection):
    return connection.execute(select(func.max(store.sync_changes.c.cursor))).scalar() or 0


@router.get("/bootstrap")
def bootstrap(_=Depends(owner)):
    with store.db() as connection:
        # Capture before reading data: any concurrent update is replayed on the next pull.
        start = cursor(connection)
        entities = {
            kind: [
                safe_record(kind, store.pack(row))
                for row in connection.execute(select(store.tables[kind])).all()
            ]
            for kind in store.SYNC_KINDS
        }
    return {
        "schema_version": 1,
        "cursor": start,
        "entities": entities,
        "scope": "Cópia privada mediante consentimento no dispositivo; originais de documentos exigem download separado.",
    }


@router.get("/pull")
def pull(after: int = Query(default=0, ge=0), _=Depends(owner)):
    with store.db() as connection:
        maximum = cursor(connection)
        if after > maximum:
            raise HTTPException(
                409,
                "O histórico do servidor foi restaurado. Exporte rascunhos e reinicialize a cópia local antes de sincronizar.",
            )
        changes = (
            connection.execute(
                select(store.sync_changes)
                .where(store.sync_changes.c.cursor > after)
                .order_by(store.sync_changes.c.cursor)
                .limit(200)
            )
            .mappings()
            .all()
        )
        result = []
        for change in changes:
            record = connection.execute(
                select(store.tables[change["kind"]]).where(
                    store.tables[change["kind"]].c.id == change["entity_id"]
                )
            ).first()
            current = safe_record(change["kind"], store.pack(record)) if record else None
            result.append({**dict(change), "record": current, "deleted": current is None})
    return {
        "changes": result,
        "cursor": changes[-1]["cursor"] if changes else after,
        "has_more": bool(changes and changes[-1]["cursor"] < maximum),
    }


class Operation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-fA-F0-9-]{36}$")
    entity_type: Literal["memories", "reminders"]
    entity_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    action: Literal["upsert", "delete"]
    base_revision: int = Field(ge=0, strict=True)
    payload: dict = Field(default_factory=dict)
    confirmed: bool = False


class Push(BaseModel):
    operations: list[Operation] = Field(min_length=1, max_length=100)


def current_state(operation, connection):
    row = connection.execute(
        select(store.tables[operation.entity_type])
        .where(store.tables[operation.entity_type].c.id == operation.entity_id)
        .with_for_update()
    ).first()
    record = store.pack(row) if row else None
    latest = connection.execute(
        select(store.sync_changes.c.revision)
        .where(
            store.sync_changes.c.kind == operation.entity_type,
            store.sync_changes.c.entity_id == operation.entity_id,
        )
        .order_by(store.sync_changes.c.cursor.desc())
        .limit(1)
    ).scalar()
    revision = int(record.get("revision", 1)) if record else (latest or 0)
    return record, revision


def apply(operation):
    digest = hashlib.sha256(
        json.dumps(operation.model_dump(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with store.transaction() as connection:
        receipt = (
            connection.execute(
                select(store.sync_receipts).where(store.sync_receipts.c.id == operation.id)
            )
            .mappings()
            .first()
        )
        current, revision = current_state(operation, connection)
        if receipt:
            if receipt["digest"] != digest:
                return {
                    "id": operation.id,
                    "status": "invalid",
                    "detail": "Identificador já usado com outro conteúdo; nada foi repetido.",
                }
            return {
                "id": operation.id,
                "status": "applied",
                "duplicate": True,
                "revision": revision,
                "record": safe_record(operation.entity_type, current),
                "deleted": current is None,
            }
        if revision != operation.base_revision or (
            current is None and revision > 0 and operation.action == "upsert"
        ):
            return {
                "id": operation.id,
                "status": "conflict",
                "revision": revision,
                "record": safe_record(operation.entity_type, current),
                "deleted": current is None,
                "detail": "Registro mudou ou foi excluído. Revise as duas versões; nenhuma sobrescrita automática.",
            }
        if (
            operation.action == "delete" or operation.entity_type == "reminders"
        ) and not operation.confirmed:
            return {
                "id": operation.id,
                "status": "invalid",
                "detail": "Confirmação explícita da operação e alvo é obrigatória.",
            }
        if operation.action == "delete":
            if current:
                if operation.entity_type == "memories":
                    memory_delete(operation.entity_id)
                else:
                    store.remove("reminders", operation.entity_id)
        elif operation.entity_type == "memories":
            memory_save(
                Memory.model_validate(operation.payload),
                operation.entity_id,
                create=current is None,
            )
        else:
            value = completed_reminder(
                Reminder.model_validate(operation.payload).model_dump(), current
            )
            store.save("reminders", value, operation.entity_id)
        current, revision = current_state(operation, connection)
        connection.execute(
            insert(store.sync_receipts).values(
                id=operation.id,
                digest=digest,
                result={
                    "kind": operation.entity_type,
                    "entity_id": operation.entity_id,
                    "revision": revision,
                },
                created=store.now(),
            )
        )
        return {
            "id": operation.id,
            "status": "applied",
            "duplicate": False,
            "revision": revision,
            "record": safe_record(operation.entity_type, current),
            "deleted": current is None,
        }


@router.post("/push")
def push(body: Push, _=Depends(owner)):
    throttle("sync", 30)
    results = []
    for operation in body.operations:
        try:
            result = apply(operation)
        except (ValidationError, ValueError, HTTPException):
            result = {
                "id": operation.id,
                "status": "invalid",
                "detail": "Campos inválidos para esta entidade; nenhuma alteração desta operação foi confirmada.",
            }
        if result["status"] != "applied" and "record" not in result:
            with store.db() as connection:
                current, revision = current_state(operation, connection)
                result.update(
                    record=safe_record(operation.entity_type, current),
                    revision=revision,
                    deleted=current is None,
                )
        results.append(result)
    return {"results": results}
