"""Private manual book authoring with immutable publication snapshots."""

import hashlib
import json
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import Field, model_validator
from sqlalchemy import insert

from . import storage as store
from .personal import MAX_IMAGE_BYTES, Args, normalize_image, remove_asset, revision
from .security import owner, throttle

router = APIRouter(prefix="/api/books", tags=["library"])


class Source(Args):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(default="", max_length=2000)
    author: str = Field(default="", max_length=300)
    license: str = Field(
        default="Referência bibliográfica; conteúdo não incorporado", max_length=500
    )
    checked_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def safe_reference(self):
        if self.url:
            try:
                parsed = urlsplit(self.url)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or any(c.isspace() or c == "\\" or ord(c) < 32 for c in self.url)
                ):
                    raise ValueError()
                _ = parsed.port
            except ValueError:
                raise ValueError("Référence URL HTTPS invalide") from None
        return self


class TextBlock(Args):
    type: Literal["text"]
    text: str = Field(min_length=1, max_length=20000)


class ImageBlock(Args):
    type: Literal["image"]
    asset_id: str = Field(max_length=64)
    alt: str = Field(min_length=1, max_length=1000)
    credit: str = Field(min_length=1, max_length=1000)


class MediaBlock(Args):
    type: Literal["audio", "video"]
    asset_id: str = Field(max_length=64)
    description: str = Field(min_length=1, max_length=1000)
    credit: str = Field(min_length=1, max_length=1000)


class QuizBlock(Args):
    type: Literal["quiz"]
    question: str = Field(min_length=1, max_length=2000)
    choices: list[str] = Field(min_length=2, max_length=8)
    correct_index: int = Field(ge=0, le=7)
    explanation: str = Field(min_length=1, max_length=3000)

    @model_validator(mode="after")
    def check_answer(self):
        if self.correct_index >= len(self.choices) or any(
            not value or len(value) > 500 for value in self.choices
        ):
            raise ValueError("Alternativas inválidas")
        return self


class CellBlock(Args):
    type: Literal["cellViewer"]
    cell_type: Literal["animal", "plant", "prokaryote"] = "animal"


class DnaBlock(Args):
    type: Literal["dnaLab"]
    sequence: str = Field(default="ATGCCATTA", pattern=r"^[ACGT]{1,60}$")


class EcologyBlock(Args):
    type: Literal["ecologyLab"]
    initial_population: int = Field(default=20, ge=1, le=1000)
    capacity: int = Field(default=100, ge=1, le=1000)
    growth_rate: float = Field(default=0.15, ge=0, le=1)


class MicroscopeBlock(Args):
    type: Literal["microscope"]
    slide: Literal["plant_schema", "animal_schema"] = "plant_schema"


Block = Annotated[
    TextBlock
    | ImageBlock
    | MediaBlock
    | QuizBlock
    | CellBlock
    | DnaBlock
    | EcologyBlock
    | MicroscopeBlock,
    Field(discriminator="type"),
]


class Page(Args):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=300)
    blocks: list[Block] = Field(default_factory=list, max_length=40)
    sources: list[Source] = Field(default_factory=list, max_length=30)


class Chapter(Args):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)
    pages: list[Page] = Field(default_factory=list, max_length=100)


class Book(Args):
    title: str = Field(min_length=1, max_length=300)
    subtitle: str = Field(default="", max_length=300)
    subject: str = Field(default="Biologia", max_length=100)
    description: str = Field(default="", max_length=3000)
    language: str = Field(default="pt-BR", max_length=30)
    author: str = Field(default="Proprietária", max_length=300)
    license: str = Field(default="Conteúdo privado; direitos reservados", max_length=1000)
    cover_asset_id: str | None = Field(default=None, max_length=64)
    cover_color: str = Field(default="#176b61", pattern=r"^#[0-9a-fA-F]{6}$")
    publication_status: Literal["draft", "review"] = "draft"
    chapters: list[Chapter] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [chapter.id for chapter in self.chapters] + [
            page.id for chapter in self.chapters for page in chapter.pages
        ]
        if len(ids) != len(set(ids)) or sum(len(c.pages) for c in self.chapters) > 500:
            raise ValueError("Identificadores repetidos ou livro acima de 500 páginas")
        return self


def validate_assets(data, book_id):
    assets = [data.get("cover_asset_id")]
    for chapter in data["chapters"]:
        for page in chapter["pages"]:
            for block in page["blocks"]:
                if "asset_id" in block:
                    asset = store.get("private_assets", block["asset_id"])
                    expected = {"image": "image/", "audio": "audio/", "video": "video/"}[
                        block["type"]
                    ]
                    if (
                        not asset
                        or asset.get("book_id") != book_id
                        or not asset.get("mime", "").startswith(expected)
                    ):
                        raise ValueError("Mídia privada indisponível ou incompatível")
    if assets[0]:
        cover = store.get("private_assets", assets[0])
        if (
            not cover
            or cover.get("book_id") != book_id
            or not cover.get("mime", "").startswith("image/")
        ):
            raise ValueError("Capa privada indisponível")


def snapshot(data, book_id, action):
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return store.save(
        "book_versions",
        {
            "book_id": book_id,
            "content": data,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "action": action,
        },
    )


def save_book(body, key=None, base_revision=None):
    with store.transaction():
        old = revision("books", key, base_revision) if key else None
        key = key or store.uid()
        data = Book.model_validate(body).model_dump(mode="json")
        validate_assets(data, key)
        version = snapshot(data, key, "manual_save")
        return store.save(
            "books",
            {
                "draft": data,
                "draft_version_id": version["id"],
                "published_version_id": old.get("published_version_id") if old else None,
            },
            key,
        )


def edition(record, selected="draft"):
    if selected == "published":
        version = store.get("book_versions", record.get("published_version_id") or "")
        if not version:
            raise HTTPException(404, "Livro ainda não publicado")
        content = version["content"]
        version_id = version["id"]
    else:
        content = record["draft"]
        version_id = record["draft_version_id"]
    return {
        **content,
        "id": record["id"],
        "revision": record.get("revision", 1),
        "edition": selected,
        "version_id": version_id,
        "published_version_id": record.get("published_version_id"),
    }


@router.get("")
def catalog(_=Depends(owner)):
    return [
        {k: v for k, v in edition(record).items() if k != "chapters"}
        for record in store.all_records("books")
    ]


class BookWrite(Args):
    data: Book
    base_revision: int | None = Field(default=None, ge=1)
    confirm: bool = False


@router.post("")
def create(body: BookWrite, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a criação manual")
    try:
        return edition(save_book(body.data.model_dump(mode="json")))
    except ValueError:
        raise HTTPException(422, "Confira as mídias e o conteúdo") from None


@router.get("/{key}")
def get_book(key: str, edition_name: Literal["draft", "published"] = "draft", _=Depends(owner)):
    record = store.get("books", key)
    if not record:
        raise HTTPException(404, "Livro não encontrado")
    return edition(record, edition_name)


@router.patch("/{key}")
def update(key: str, body: BookWrite, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a edição manual")
    try:
        return edition(save_book(body.data.model_dump(mode="json"), key, body.base_revision))
    except ValueError:
        raise HTTPException(422, "Confira as mídias e o conteúdo") from None


class VersionAction(Args):
    base_revision: int
    confirm: bool = False


@router.post("/{key}/publish")
def publish(key: str, body: VersionAction, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme explicitamente a publicação revisada")
    with store.transaction():
        record = revision("books", key, body.base_revision)
        if record["draft"]["publication_status"] != "review":
            raise HTTPException(409, "Marque como revisão antes de publicar")
        if not any(
            page["blocks"] for chapter in record["draft"]["chapters"] for page in chapter["pages"]
        ):
            raise HTTPException(422, "Livro sem conteúdo")
        version = snapshot(
            {**record["draft"], "publication_status": "published"}, key, "manual_publish"
        )
        saved = store.save("books", {**record, "published_version_id": version["id"]}, key)
    return edition(saved, "published")


@router.get("/{key}/versions")
def versions(key: str, _=Depends(owner)):
    if not store.get("books", key):
        raise HTTPException(404, "Livro não encontrado")
    return [
        {k: v for k, v in record.items() if k != "content"}
        for record in store.all_records("book_versions")
        if record["book_id"] == key
    ]


@router.post("/{key}/revert/{version_id}")
def revert(key: str, version_id: str, body: VersionAction, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a restauração como rascunho")
    with store.transaction():
        revision("books", key, body.base_revision)
        version = store.get("book_versions", version_id)
        if not version or version["book_id"] != key:
            raise HTTPException(404, "Versão não encontrada")
        return edition(
            save_book(
                {**version["content"], "publication_status": "draft"}, key, body.base_revision
            )
        )


@router.get("/{key}/export")
def export_book(key: str, _=Depends(owner)):
    record = store.get("books", key)
    if not record:
        raise HTTPException(404, "Livro não encontrado")
    return {
        "format": "saly-book-v1",
        "book": edition(record),
        "note": "Mídias binárias não incluídas; referências de assets privados precisam do backup do banco.",
    }


@router.delete("/{key}")
def delete_book(key: str, base_revision: int, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme excluir livro, versões, progresso, notas e mídias")
    with store.transaction():
        revision("books", key, base_revision)
        for kind in ("book_versions", "book_annotations", "reading_progress"):
            for item in store.all_records(kind):
                if item.get("book_id") == key:
                    store.remove(kind, item["id"])
        for asset in store.all_records("private_assets"):
            if asset.get("book_id") == key:
                remove_asset(asset["id"])
        store.remove("books", key)
    return {"deleted": True}


@router.post("/{key}/image")
def upload_image(key: str, file: UploadFile = File(...), _=Depends(owner)):
    throttle("book-image", 20)
    content = normalize_image(file.file.read(MAX_IMAGE_BYTES + 1))
    with store.transaction() as connection:
        if not store.get("books", key):
            raise HTTPException(404, "Livro não encontrado")
        asset = store.save(
            "private_assets",
            {
                "book_id": key,
                "mime": "image/png",
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            },
        )
        connection.execute(insert(store.asset_contents).values(id=asset["id"], content=content))
    return asset


@router.delete("/{key}/assets/{asset_id}")
def delete_asset(key: str, asset_id: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme excluir a mídia sem referência")
    with store.transaction():
        asset = store.get("private_assets", asset_id)
        if not asset or asset.get("book_id") != key:
            raise HTTPException(404, "Mídia não encontrada")
        for version in store.all_records("book_versions"):
            if version["book_id"] == key and asset_id in json.dumps(version["content"]):
                raise HTTPException(
                    409, "Mídia referenciada em uma versão; preserve-a até excluir o livro"
                )
        remove_asset(asset_id)
    return {"deleted": True}


class Progress(Args):
    current_page_id: str | None = None
    completed_pages: list[str] = Field(default_factory=list, max_length=500)
    bookmarks: list[str] = Field(default_factory=list, max_length=500)
    quiz_attempts: dict[str, list[int]] = Field(default_factory=dict, max_length=1000)
    base_revision: int = Field(default=0, ge=0)


def page_ids(key):
    record = store.get("books", key)
    if not record:
        raise HTTPException(404, "Livro não encontrado")
    contents = [record["draft"]]
    if record.get("published_version_id"):
        contents.append(store.get("book_versions", record["published_version_id"])["content"])
    return {
        page["id"] for data in contents for chapter in data["chapters"] for page in chapter["pages"]
    }


@router.get("/{key}/progress")
def progress(key: str, _=Depends(owner)):
    page_ids(key)
    return store.get("reading_progress", key) or {
        "book_id": key,
        "revision": 0,
        "current_page_id": None,
        "completed_pages": [],
        "bookmarks": [],
        "quiz_attempts": {},
    }


@router.put("/{key}/progress")
def save_progress(key: str, body: Progress, _=Depends(owner)):
    with store.transaction():
        known = page_ids(key)
        if (
            not set(
                body.completed_pages
                + body.bookmarks
                + ([body.current_page_id] if body.current_page_id else [])
            )
            <= known
        ):
            raise HTTPException(422, "Página não pertence a esta edição")
        previous = store.get("reading_progress", key)
        if body.base_revision != (previous.get("revision", 1) if previous else 0):
            raise HTTPException(409, "Progresso mudou em outra aba; recarregue")
        if any(
            len(values) > 100
            or any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 7 for v in values)
            for values in body.quiz_attempts.values()
        ):
            raise HTTPException(422, "Tentativas inválidas")
        data = body.model_dump(exclude={"base_revision"})
        return store.save("reading_progress", {**data, "book_id": key}, key)


class Annotation(Args):
    page_id: str
    selected_text: str = Field(default="", max_length=3000)
    note: str = Field(min_length=1, max_length=5000)
    confirm: bool = False


@router.get("/{key}/annotations")
def annotations(key: str, _=Depends(owner)):
    page_ids(key)
    return [a for a in store.all_records("book_annotations") if a["book_id"] == key]


@router.post("/{key}/annotations")
def annotate(key: str, body: Annotation, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme guardar a anotação")
    if body.page_id not in page_ids(key):
        raise HTTPException(422, "Página não encontrada")
    return store.save("book_annotations", {"book_id": key, **body.model_dump(exclude={"confirm"})})


@router.delete("/{key}/annotations/{annotation_id}")
def delete_annotation(key: str, annotation_id: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão da anotação")
    with store.transaction():
        record = store.get("book_annotations", annotation_id)
        if not record or record["book_id"] != key:
            raise HTTPException(404, "Anotação não encontrada")
        store.remove("book_annotations", annotation_id)
    return {"deleted": True}
