"""Owner-only review of bundled Core versions. Never install policies from arbitrary JSON."""

import hashlib
import json
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import update

from .. import storage as store
from ..imports import validation_details
from ..security import owner
from .policy import DATA, CoreSeed, activate, core_status, read_bundle

router = APIRouter(prefix="/api/core", tags=["core-administration"])


class Candidate(BaseModel):
    document: dict


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@router.post("/preview")
def preview(body: Candidate, _=Depends(owner)):
    if len(json.dumps(body.document)) > 500_000:
        raise HTTPException(413, "Core excede o limite de 500 KB")
    try:
        seed = CoreSeed.model_validate(body.document)
    except ValidationError as error:
        raise HTTPException(
            422,
            {
                "message": "Core incompatível com o schema conhecido",
                "errors": validation_details(error.errors()),
            },
        ) from None
    bundled, manifest = read_bundle(DATA)
    compatible = canonical(body.document) == canonical(
        json.loads((DATA / manifest.file).read_bytes())
    )
    record = store.save(
        "core_imports",
        {
            "status": "previewed",
            "compatible": compatible,
            "digest": canonical(body.document),
            "bundle_sha256": manifest.sha256,
            "schema_version": seed.versao_esquema,
            "rules": len(seed.regras_inviolaveis_propostas),
            "domains": len(seed.conhecimento_cientifico_base),
            "changes": {
                "rules_before": len(bundled.regras_inviolaveis_propostas),
                "rules_after": len(seed.regras_inviolaveis_propostas),
            },
        },
    )
    return {
        **record,
        "already_active": compatible and core_status()["sha256"] == manifest.sha256,
        "notice": "Semente compatível com a versão revisada distribuída. A confirmação registra backup e verifica a ativação sem criar memórias pessoais."
        if compatible
        else "O conteúdo difere da versão revisada. A migração está bloqueada: revise o pacote/manifesto no repositório antes de distribuir novas políticas. Nenhuma instrução deste JSON foi instalada.",
    }


class Confirmation(BaseModel):
    confirm: bool
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.post("/imports/{key}/confirm")
def confirm(key: str, body: Confirmation, _=Depends(owner)):
    record = store.get("core_imports", key)
    if not record or record["status"] != "previewed":
        raise HTTPException(409, "Prévia ausente ou já utilizada")
    if not body.confirm or body.digest != record["digest"]:
        raise HTTPException(400, "Confirme exatamente a versão apresentada na prévia")
    if not record["compatible"] or record["bundle_sha256"] != core_status()["sha256"]:
        raise HTTPException(409, "Migração exige uma versão revisada no manifesto do repositório")
    if (datetime.now(UTC) - datetime.fromisoformat(record["created"])).total_seconds() > 900:
        raise HTTPException(409, "Prévia expirada; selecione o arquivo novamente")
    with store.db() as connection:
        updated = connection.execute(
            update(store.tables["core_imports"])
            .where(
                store.tables["core_imports"].c.id == key,
                store.tables["core_imports"].c.data["status"].as_string() == "previewed",
            )
            .values(
                data={
                    **{k: v for k, v in record.items() if k not in ("id", "created", "updated")},
                    "status": "running",
                }
            )
        )
        if updated.rowcount != 1:
            raise HTTPException(409, "Prévia já utilizada")
    try:
        directory = store.DATA / "core-backups"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        backup = {
            "format": "saly-core-backup-v1",
            "created": store.now(),
            "active": store.setting("core_active"),
            "document": json.loads((DATA / "SALY_CORE_MEMORY_v1.json").read_bytes()),
        }
        path = directory / (record["id"] + ".json")
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            json.dump(backup, output, ensure_ascii=False, indent=2)
        activate()
        store.save(
            "core_imports", {**record, "status": "completed", "finished_at": store.now()}, key
        )
        store.audit("core_review", "Semente revisada, backup criado e ativação verificada: " + key)
        return {
            "status": "completed",
            "core": core_status(),
            "memories_created": 0,
            "backup_url": f"/api/core/imports/{key}/backup",
        }
    except Exception:  # noqa: BLE001 - sanitize administrative/storage errors
        store.save("core_imports", {**record, "status": "failed"}, key)
        raise HTTPException(
            503, "Verificação administrativa não concluída; confira o diagnóstico local"
        ) from None


@router.get("/imports/{key}/backup")
def download_backup(key: str, _=Depends(owner)):
    record = store.get("core_imports", key)
    if not record or record["status"] != "completed":
        raise HTTPException(404, "Backup não disponível")
    path = store.DATA / "core-backups" / (record["id"] + ".json")
    if not path.is_file():
        raise HTTPException(404, "Backup não encontrado no armazenamento")
    return FileResponse(path, media_type="application/json", filename="saly-core-backup.json")
