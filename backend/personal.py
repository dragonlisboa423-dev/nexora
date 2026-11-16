"""Manual purchases and link drawers. Private images; no OCR, crawling or payments."""

import hashlib
import io
import re
import warnings
from datetime import date, datetime
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, insert, select

from . import storage as store
from .planning import save_alarm
from .security import owner, throttle

router = APIRouter(prefix="/api", tags=["personal"])
Image.MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Purchase(Args):
    product: str = Field(min_length=1, max_length=300)
    price_cents: int = Field(ge=0, le=1_000_000_000, strict=True)
    quantity: int = Field(default=1, ge=1, le=10000, strict=True)
    store_name: str = Field(default="", max_length=300)
    purchased_on: date | None = None
    category: str = Field(default="outros", min_length=1, max_length=80)
    shipping_cents: int = Field(default=0, ge=0, le=1_000_000_000, strict=True)
    discount_cents: int = Field(default=0, ge=0, le=1_000_000_000, strict=True)
    payment_method: str = Field(default="", max_length=100)
    installments: int | None = Field(default=None, ge=1, le=120, strict=True)
    status: Literal["purchased", "awaiting", "delivered", "wishlist", "planned", "cancelled"] = (
        "purchased"
    )
    expected_on: date | None = None
    received_on: date | None = None
    warranty_until: date | None = None
    return_until: date | None = None
    notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def check_total(self):
        if self.discount_cents > self.price_cents * self.quantity + self.shipping_cents:
            raise ValueError("Desconto maior que o valor da compra")
        if self.status in {"purchased", "awaiting", "delivered"} and not self.purchased_on:
            raise ValueError("Informe a data da compra realizada")
        return self


class Drawer(Args):
    name: str = Field(min_length=1, max_length=150)
    color: str = Field(default="#7acfc1", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Literal["folder", "book", "star", "science", "home"] = "folder"
    position: int = Field(default=0, ge=0, le=100000, strict=True)


class Link(Args):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=2000)
    description: str = Field(default="", max_length=2000)
    drawer_id: str = Field(min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list, max_length=30)
    position: int = Field(default=0, ge=0, le=100000, strict=True)
    favorite: bool = False
    allow_http: bool = False

    @model_validator(mode="after")
    def check_url(self):
        if re.search(r"[\s\\\x00-\x1f\x7f]", self.url):
            raise ValueError("URL contém caracteres inválidos")
        try:
            parsed = urlsplit(self.url)
            valid = parsed.scheme in ({"https", "http"} if self.allow_http else {"https"})
            if not valid or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError()
            _ = parsed.port
        except ValueError:
            raise ValueError(
                "Use HTTPS ou permita HTTP explicitamente; sem credenciais na URL"
            ) from None
        if any(len(tag) > 80 for tag in self.tags):
            raise ValueError("Etiqueta muito longa")
        return self


MODELS = {"purchases": Purchase, "drawers": Drawer, "links": Link}


def normalize(kind, payload):
    data = MODELS[kind].model_validate(payload).model_dump(mode="json")
    if kind == "links" and not store.get("drawers", data["drawer_id"]):
        raise ValueError("Gaveta não encontrada")
    if kind == "purchases":
        data["total_cents"] = (
            data["price_cents"] * data["quantity"] + data["shipping_cents"] - data["discount_cents"]
        )
    return data


def revision(kind, key, expected):
    previous = store.get(kind, key)
    if not previous:
        raise HTTPException(404, "Registro não encontrado")
    if expected != previous.get("revision", 1):
        raise HTTPException(409, "Registro mudou em outra aba; recarregue antes de salvar")
    return previous


def save_personal(kind, payload, key=None, base_revision=None, create=False):
    with store.transaction():
        old = revision(kind, key, base_revision) if key and not create else None
        data = normalize(kind, payload)
        if kind == "purchases" and old:
            data["image_id"] = old.get("image_id")
            data["alarm_ids"] = old.get("alarm_ids", [])
        return store.save(kind, data, key)


def delete_personal(kind, key, base_revision):
    with store.transaction():
        record = revision(kind, key, base_revision)
        if kind == "drawers":
            for link in store.all_records("links"):
                if link["drawer_id"] == key:
                    store.remove("links", link["id"])
        if kind == "purchases":
            if record.get("image_id"):
                remove_asset(record["image_id"])
            from .planning import cancel_occurrences

            for alarm_id in record.get("alarm_ids", []):
                alarm = store.get("alarms", alarm_id)
                if alarm:
                    store.save("alarms", {**alarm, "enabled": False, "next_due_at": None}, alarm_id)
                    cancel_occurrences(alarm_id)
        store.remove(kind, key)


class Write(Args):
    data: dict
    base_revision: int | None = Field(default=None, ge=1)
    confirm: bool = False


def crud(kind):
    def listing(_=Depends(owner)):
        return store.all_records(kind)

    def create(body: Write, _=Depends(owner)):
        if not body.confirm:
            raise HTTPException(400, "Confirme a criação")
        try:
            return save_personal(kind, body.data)
        except ValueError:
            raise HTTPException(
                422, "Confira os campos e a gaveta; use a prévia para detalhes"
            ) from None

    def update(key: str, body: Write, _=Depends(owner)):
        if not body.confirm:
            raise HTTPException(400, "Confirme a alteração")
        try:
            return save_personal(kind, body.data, key, body.base_revision)
        except ValueError:
            raise HTTPException(
                422, "Confira os campos e a gaveta; use a prévia para detalhes"
            ) from None

    def remove(key: str, base_revision: int, confirm: bool = False, _=Depends(owner)):
        if not confirm:
            raise HTTPException(400, "Confirme a exclusão e os registros associados")
        delete_personal(kind, key, base_revision)
        return {"deleted": True}

    router.add_api_route(f"/{kind}", listing, methods=["GET"], name=f"list_{kind}")
    router.add_api_route(f"/{kind}", create, methods=["POST"], name=f"create_{kind}")
    router.add_api_route(f"/{kind}/{{key}}", update, methods=["PATCH"], name=f"update_{kind}")
    router.add_api_route(f"/{kind}/{{key}}", remove, methods=["DELETE"], name=f"delete_{kind}")


for _kind in MODELS:
    crud(_kind)


@router.post("/purchases/preview")
def purchase_preview(body: Purchase, _=Depends(owner)):
    return normalize("purchases", body.model_dump())


@router.post("/links/preview")
def link_preview(body: Link, _=Depends(owner)):
    try:
        return normalize("links", body.model_dump())
    except ValueError:
        raise HTTPException(422, "Gaveta não encontrada") from None


class Budget(Args):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount_cents: int = Field(ge=0, le=100_000_000_000, strict=True)
    confirm: bool = False


@router.put("/purchases-budget")
def budget(body: Budget, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme o orçamento")
    with store.transaction():
        budgets = store.setting("purchase_budgets", {})
        budgets[body.month] = body.amount_cents
        store.set_setting("purchase_budgets", budgets)
    return {"month": body.month, "amount_cents": body.amount_cents}


@router.get("/purchases-summary")
def summary(month: str, _=Depends(owner)):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(422, "Mês inválido")
    records = [
        p
        for p in store.all_records("purchases")
        if (p.get("purchased_on") or "").startswith(month)
        and p["status"] in {"purchased", "awaiting", "delivered"}
    ]
    categories = {}
    for p in records:
        categories[p["category"]] = categories.get(p["category"], 0) + p["total_cents"]
    total = sum(categories.values())
    amount = store.setting("purchase_budgets", {}).get(month)
    return {
        "month": month,
        "total_cents": total,
        "count": len(records),
        "categories": categories,
        "budget_cents": amount,
        "remaining_cents": None if amount is None else amount - total,
        "installments": [
            {
                "id": p["id"],
                "product": p["product"],
                "count": p["installments"],
                "base_cents": p["total_cents"] // p["installments"],
                "remainder_cents": p["total_cents"] % p["installments"],
            }
            for p in records
            if p.get("installments")
        ],
    }


def remove_asset(key):
    with store.db() as connection:
        connection.execute(delete(store.asset_contents).where(store.asset_contents.c.id == key))
        store.remove("private_assets", key)


@router.get("/private-assets/{key}")
def image(key: str, _=Depends(owner)):
    record = store.get("private_assets", key)
    with store.db() as connection:
        content = connection.execute(
            select(store.asset_contents.c.content).where(store.asset_contents.c.id == key)
        ).scalar()
    if content is None:
        raise HTTPException(404, "Imagem não encontrada")
    return Response(
        content,
        media_type=(record or {}).get("mime", "application/octet-stream"),
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="saly-{key}.{ {"image/png": "png", "video/mp4": "mp4", "audio/wav": "wav"}.get((record or {}).get("mime"), "bin") }"',
        },
    )


def normalize_image(raw):
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Imagem acima de 8 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if (
                    source.format not in {"JPEG", "PNG", "WEBP"}
                    or getattr(source, "n_frames", 1) != 1
                ):
                    raise ValueError()
                source.load()
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((2400, 2400))
                normalized.info.clear()
                output = io.BytesIO()
                normalized.save(output, format="PNG", optimize=True)
                content = output.getvalue()
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            422, "Imagem inválida; use PNG, JPEG ou WebP estático até 16 megapixels"
        ) from None
    return content


@router.post("/purchases/{key}/image")
def upload_image(key: str, base_revision: int, file: UploadFile = File(...), _=Depends(owner)):
    throttle("receipt-image", limit=20)
    raw = file.file.read(MAX_IMAGE_BYTES + 1)
    content = normalize_image(raw)
    asset_id = store.uid()
    with store.transaction() as connection:
        purchase = revision("purchases", key, base_revision)
        store.save(
            "private_assets",
            {
                "purchase_id": key,
                "mime": "image/png",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            asset_id,
        )
        connection.execute(insert(store.asset_contents).values(id=asset_id, content=content))
        result = store.save("purchases", {**purchase, "image_id": asset_id}, key)
        if purchase.get("image_id"):
            remove_asset(purchase["image_id"])
    return result


@router.delete("/purchases/{key}/image")
def delete_image(key: str, base_revision: int, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão do comprovante")
    with store.transaction():
        purchase = revision("purchases", key, base_revision)
        asset_id = purchase.get("image_id")
        result = store.save("purchases", {**purchase, "image_id": None}, key)
        if asset_id:
            remove_asset(asset_id)
    return result


class PurchaseAlert(Args):
    field: Literal["expected_on", "warranty_until", "return_until"]
    days_before: int = Field(default=1, ge=0, le=365)
    local_time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = "America/Sao_Paulo"
    base_revision: int
    confirm: bool = False


@router.post("/purchases/{key}/alarm")
def purchase_alarm(key: str, body: PurchaseAlert, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a criação do alarme")
    from datetime import timedelta

    with store.transaction():
        purchase = revision("purchases", key, body.base_revision)
        if not purchase.get(body.field):
            raise HTTPException(422, "Cadastre primeiro a data escolhida")
        day = date.fromisoformat(purchase[body.field]) - timedelta(days=body.days_before)
        try:
            record = save_alarm(
                {
                    "title": f"Compra: {purchase['product']}",
                    "message": {
                        "expected_on": "Conferir previsão manual de entrega",
                        "warranty_until": "Fim da garantia",
                        "return_until": "Prazo de devolução",
                    }[body.field],
                    "scheduled_at": datetime.combine(
                        day, datetime.strptime(body.local_time, "%H:%M").time()
                    ).isoformat(),
                    "timezone": body.timezone,
                }
            )
        except ValueError:
            raise HTTPException(422, "Horário/fuso inválido") from None
        store.save(
            "purchases",
            {**purchase, "alarm_ids": [*purchase.get("alarm_ids", []), record["id"]]},
            key,
        )
    return record


@router.get("/personal-export")
def personal_export(_=Depends(owner)):
    return {
        "format": "saly-personal-v1",
        "purchases": [
            {k: v for k, v in p.items() if k not in {"image_id", "alarm_ids"}}
            for p in store.all_records("purchases")
        ],
        "drawers": store.all_records("drawers"),
        "links": store.all_records("links"),
        "budgets": store.setting("purchase_budgets", {}),
        "note": "Imagens e alarmes não estão incluídos; exporte-os separadamente.",
    }


class SpaceImport(Args):
    format: Literal["saly-space-v1"]
    drawers: list[dict] = Field(max_length=300)
    links: list[dict] = Field(max_length=3000)
    confirm: bool = False


@router.post("/space-import")
def import_space(body: SpaceImport, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a importação aditiva; novos IDs serão criados")
    with store.transaction():
        mapping = {}
        try:
            for entry in body.drawers:
                old_id = entry.get("id")
                if not old_id or old_id in mapping:
                    raise ValueError()
                payload = {
                    k: v
                    for k, v in entry.items()
                    if k not in {"id", "created", "updated", "revision"}
                }
                mapping[old_id] = save_personal("drawers", payload)["id"]
            for entry in body.links:
                payload = {
                    k: v
                    for k, v in entry.items()
                    if k not in {"id", "created", "updated", "revision"}
                }
                payload["drawer_id"] = mapping[payload["drawer_id"]]
                save_personal("links", payload)
        except (ValueError, KeyError):
            raise HTTPException(422, "Organização inválida; nada foi importado") from None
    return {"drawers": len(mapping), "links": len(body.links)}
