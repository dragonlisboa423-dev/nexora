"""Additive visual purchases: product photo separate from receipts, manual savings goals.
No prices, balances or savings are inferred. Existing purchase accounting is unchanged.
"""

import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert

from . import storage as store
from .personal import MAX_IMAGE_BYTES, normalize_image, remove_asset, revision
from .security import owner, throttle

router = APIRouter(prefix="/api", tags=["purchase-visual"])


@router.post("/purchases/{key}/product-photo")
def product_photo(key: str, base_revision: int, file: UploadFile = File(...), _=Depends(owner)):
    throttle("product-photo", limit=20)
    content = normalize_image(file.file.read(MAX_IMAGE_BYTES + 1))
    asset_id = store.uid()
    with store.transaction() as connection:
        record = revision("purchases", key, base_revision)
        previous = record.get("product_image_id")
        try:
            store.check_asset_capacity(len(content), previous)
        except ValueError as error:
            raise HTTPException(413, str(error)) from None
        store.save(
            "private_assets",
            {
                "purchase_id": key,
                "purpose": "product_photo",
                "mime": "image/png",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            asset_id,
        )
        connection.execute(insert(store.asset_contents).values(id=asset_id, content=content))
        saved = store.save("purchases", {**record, "product_image_id": asset_id}, key)
        if previous:
            remove_asset(previous)
    return saved


@router.delete("/purchases/{key}/product-photo")
def remove_product_photo(key: str, base_revision: int, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão da foto do produto")
    with store.transaction():
        record = revision("purchases", key, base_revision)
        saved = store.save("purchases", {**record, "product_image_id": None}, key)
        if record.get("product_image_id"):
            remove_asset(record["product_image_id"])
    return saved


class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    target_cents: int = Field(gt=0, le=100_000_000_000, strict=True)
    saved_cents: int = Field(default=0, ge=0, le=100_000_000_000, strict=True)
    base_revision: int = Field(default=0, ge=0, strict=True)
    confirm: bool = False


@router.get("/savings-goals")
def savings_goals(_=Depends(owner)):
    return list(store.setting("purchase_savings_goals", {}).values())


def save_goal(body, key=None):
    if not body.confirm:
        raise HTTPException(400, "Confirme os valores informados da meta")
    with store.transaction():
        goals = store.setting("purchase_savings_goals", {})
        if not key and len(goals) >= 30:
            raise HTTPException(413, "Até trinta metas; exclua uma antes de continuar")
        previous = goals.get(key)
        if key and not previous:
            raise HTTPException(404, "Meta não encontrada")
        if (previous or {}).get("revision", 0) != body.base_revision:
            raise HTTPException(409, "Meta alterada em outra aba; recarregue antes de salvar")
        key = key or store.uid()
        record = {
            "id": key,
            "title": body.title,
            "target_cents": body.target_cents,
            "saved_cents": body.saved_cents,
            "revision": body.base_revision + 1,
            "updated": store.now(),
        }
        goals[key] = record
        store.set_setting("purchase_savings_goals", goals)
        store.audit("savings_goal", "Meta manual atualizada: " + key)
    return record


@router.post("/savings-goals")
def create_goal(body: Goal, _=Depends(owner)):
    return save_goal(body)


@router.put("/savings-goals/{key}")
def update_goal(key: str, body: Goal, _=Depends(owner)):
    return save_goal(body, key)


@router.delete("/savings-goals/{key}")
def delete_goal(key: str, base_revision: int, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão da meta")
    with store.transaction():
        goals = store.setting("purchase_savings_goals", {})
        if key not in goals:
            raise HTTPException(404, "Meta não encontrada")
        if goals[key]["revision"] != base_revision:
            raise HTTPException(409, "Meta alterada; recarregue antes de excluir")
        del goals[key]
        store.set_setting("purchase_savings_goals", goals)
    return {"deleted": True}
