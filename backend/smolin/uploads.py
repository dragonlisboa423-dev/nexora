"""Small authenticated resumable requests avoid proxy limits on large originals."""

import hashlib
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import storage as store
from ..security import owner
from . import service
from .formats import safe_name

router = APIRouter(prefix="/api/knowledge/uploads", tags=["smolin-transfer"])
CHUNK = 2 * 1024 * 1024


def path(key):
    if not re.fullmatch("[a-f0-9]{32}", key):
        raise HTTPException(404, "Transferência não encontrada")
    folder = store.DATA / "smolin-uploads"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder / (key + ".part")


def cleanup():
    expiry = datetime.now(UTC) - timedelta(hours=24)
    records = store.all_records("smolin_uploads")
    known = {record["id"] for record in records}
    folder = store.DATA / "smolin-uploads"
    if folder.is_dir():
        for temporary in folder.glob("*.part"):
            if (
                temporary.stem not in known
                and datetime.fromtimestamp(temporary.stat().st_mtime, UTC) < expiry
            ):
                temporary.unlink(missing_ok=True)
    for record in records:
        if datetime.fromisoformat(record["updated"]) < expiry:
            path(record["id"]).unlink(missing_ok=True)
            store.remove("smolin_uploads", record["id"])


class Start(BaseModel):
    name: str = Field(min_length=1, max_length=1000)
    size: int = Field(gt=0, strict=True)


@router.post("")
def start(body: Start, _=Depends(owner)):
    if body.size > service.upload_limit():
        raise HTTPException(413, "Arquivo acima do limite do Centro Smolin")
    with store.transaction():
        cleanup()
        active = store.all_records("smolin_uploads")
        used = sum(service.storage_cost(d) for d in service.catalog()) + sum(
            d["size"] for d in active
        )
        import os

        if used + body.size > int(os.environ.get("SALY_MAX_TOTAL_MB", "200")) * 1024 * 1024:
            raise HTTPException(413, "Transferências e acervo atingiram a capacidade configurada")
        if len(active) >= 3:
            raise HTTPException(
                429, "Até três transferências simultâneas; cancele ou conclua as anteriores"
            )
        record = store.save(
            "smolin_uploads", {"name": safe_name(body.name), "size": body.size, "offset": 0}
        )
        with path(record["id"]).open("xb"):
            pass
        path(record["id"]).chmod(0o600)
    return {**record, "chunk_bytes": CHUNK}


@router.get("")
def list_transfers(_=Depends(owner)):
    cleanup()
    return store.all_records("smolin_uploads")


@router.get("/{key}")
def transfer_status(key: str, _=Depends(owner)):
    record = store.get("smolin_uploads", key)
    if not record or not path(key).is_file():
        raise HTTPException(404, "Transferência ausente ou expirada")
    # Validate every confirmed byte when reselecting a file, not just its filename.
    digest = hashlib.sha256()
    with path(key).open("rb") as source:
        remaining = record["offset"]
        while remaining:
            part = source.read(min(2 * 1024 * 1024, remaining))
            if not part:
                raise HTTPException(409, "Temporário incompleto; reinicie o envio")
            digest.update(part)
            remaining -= len(part)
    blocks = []
    with path(key).open("rb") as source:
        remaining = record["offset"]
        while remaining:
            part = source.read(min(CHUNK, remaining))
            blocks.append(hashlib.sha256(part).hexdigest())
            remaining -= len(part)
    return {
        **record,
        "prefix_sha256": digest.hexdigest(),
        "block_sha256": blocks,
        "chunk_bytes": CHUNK,
    }


@router.put("/{key}")
async def chunk(key: str, request: Request, offset: int, _=Depends(owner)):
    raw = bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw) > CHUNK:
            raise HTTPException(413, "Bloco acima de 2 MB")
    if not raw or offset < 0:
        raise HTTPException(422, "Bloco vazio ou posição inválida")
    with store.transaction():
        record = store.get("smolin_uploads", key)
        if not record:
            raise HTTPException(404, "Transferência não encontrada ou expirada")
        file = path(key)
        if not file.is_file():
            raise HTTPException(409, "Transferência interrompida; reinicie o envio")
        if offset < record["offset"]:
            with file.open("rb") as source:
                source.seek(offset)
                previous = source.read(len(raw))
            if offset + len(raw) <= record["offset"] and previous == raw:
                return {"offset": record["offset"], "duplicate": True}
            raise HTTPException(409, "Reenvio tem conteúdo diferente")
        if offset != record["offset"] or offset + len(raw) > record["size"]:
            raise HTTPException(409, "Posição inválida; reinicie ou retome da posição confirmada")
        with file.open("r+b") as target:
            target.truncate(record["offset"])
            target.seek(offset)
            target.write(raw)
            target.flush()
        updated = store.save("smolin_uploads", {**record, "offset": offset + len(raw)}, key)
    return {"offset": updated["offset"]}


@router.post("/{key}/complete")
async def complete(key: str, _=Depends(owner)):
    with store.transaction():
        record = store.get("smolin_uploads", key)
        if not record:
            raise HTTPException(404, "Transferência não encontrada")
        if record["offset"] != record["size"]:
            raise HTTPException(409, "Transferência incompleta")
        file = path(key)
        if file.stat().st_size != record["size"]:
            raise HTTPException(409, "Arquivo temporário incompleto")
        result = service.upload(file.read_bytes(), record["name"])
        store.remove("smolin_uploads", key)
    file.unlink(missing_ok=True)
    if result.get("job_id"):
        service.start(result["id"], result["job_id"])
    return result


@router.delete("/{key}")
def cancel(key: str, _=Depends(owner)):
    with store.transaction():
        if store.get("smolin_uploads", key):
            store.remove("smolin_uploads", key)
        path(key).unlink(missing_ok=True)
    return {"cancelled": True}
