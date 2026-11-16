import copy
import io

from PIL import Image

from backend import storage as store


def book(**values):
    return {
        "title": "Livro de teste",
        "chapters": [
            {
                "id": "chapter1",
                "title": "Capítulo inicial",
                "pages": [
                    {
                        "id": "page1",
                        "title": "Primeira página",
                        "blocks": [
                            {"type": "text", "text": "Texto original de teste."},
                            {
                                "type": "quiz",
                                "question": "2+2?",
                                "choices": ["3", "4"],
                                "correct_index": 1,
                                "explanation": "A soma é 4.",
                            },
                        ],
                    }
                ],
            }
        ],
        **values,
    }


def create(client, data=None):
    result = client.post("/api/books", json={"data": data or book(), "confirm": True})
    assert result.status_code == 200, result.text
    return result.json()


def test_manual_draft_review_publication_is_immutable_and_revert_is_draft(client):
    created = create(client)
    path = "/api/books/" + created["id"]
    assert client.get(path + "?edition_name=published").status_code == 404
    assert (
        client.post(path + "/publish", json={"base_revision": 1, "confirm": True}).status_code
        == 409
    )
    data = book(publication_status="review")
    saved = client.patch(path, json={"data": data, "base_revision": 1, "confirm": True}).json()
    published = client.post(
        path + "/publish", json={"base_revision": saved["revision"], "confirm": True}
    )
    assert published.status_code == 200, published.text
    assert published.json()["publication_status"] == "published"
    original = published.json()["version_id"]
    data["title"] = "Rascunho alterado"
    changed = client.patch(path, json={"data": data, "base_revision": 3, "confirm": True})
    assert changed.status_code == 200, changed.text
    assert client.get(path + "?edition_name=published").json()["title"] == "Livro de teste"
    assert client.get(path + "?edition_name=published").json()["version_id"] == original
    assert (
        client.patch(path, json={"data": data, "base_revision": 3, "confirm": True}).status_code
        == 409
    )
    reverted = client.post(path + "/revert/" + original, json={"base_revision": 4, "confirm": True})
    assert reverted.status_code == 200 and reverted.json()["publication_status"] == "draft"
    assert client.get(path + "?edition_name=published").json()["version_id"] == original
    assert client.get(path + "/export").json()["format"] == "saly-book-v1"


def test_reader_progress_quiz_notes_conflict_and_deletion(client):
    created = create(client)
    path = "/api/books/" + created["id"]
    body = {
        "current_page_id": "page1",
        "completed_pages": ["page1"],
        "bookmarks": ["page1"],
        "quiz_attempts": {"q1": [0, 1]},
        "base_revision": 0,
    }
    saved = client.put(path + "/progress", json=body)
    assert saved.status_code == 200 and saved.json()["revision"] == 1
    assert client.put(path + "/progress", json=body).status_code == 409
    assert (
        client.put(
            path + "/progress", json={**body, "base_revision": 1, "current_page_id": "otherpage"}
        ).status_code
        == 422
    )
    note = client.post(
        path + "/annotations",
        json={"page_id": "page1", "note": "Revisar conceito", "confirm": True},
    )
    assert note.status_code == 200
    store.engine.dispose()
    store.initialize()
    assert client.get(path + "/progress").json()["quiz_attempts"]["q1"] == [0, 1]
    assert client.get(path + "/annotations").json()[0]["note"] == "Revisar conceito"
    assert (
        client.delete(
            path + "?base_revision=1&confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    for kind in ("books", "book_versions", "book_annotations", "reading_progress"):
        assert not store.all_records(kind)


def test_blocks_reject_code_unsafe_urls_unknown_configuration_and_cross_book_assets(client):
    for block in (
        {"type": "script", "code": "alert(1)"},
        {"type": "dnaLab", "sequence": "javascript"},
        {"type": "cellViewer", "cell_type": "virus"},
        {
            "type": "quiz",
            "question": "x",
            "choices": ["a", "b"],
            "correct_index": 5,
            "explanation": "x",
        },
    ):
        data = book()
        data["chapters"][0]["pages"][0]["blocks"] = [block]
        assert client.post("/api/books", json={"data": data, "confirm": True}).status_code == 422
    data = book()
    data["chapters"][0]["pages"][0]["sources"] = [{"title": "evil", "url": "javascript:alert(1)"}]
    assert client.post("/api/books", json={"data": data, "confirm": True}).status_code == 422
    data = book()
    data["chapters"][0]["pages"].append(copy.deepcopy(data["chapters"][0]["pages"][0]))
    assert client.post("/api/books", json={"data": data, "confirm": True}).status_code == 422
    a = create(client)
    b = create(client)
    stream = io.BytesIO()
    Image.new("RGB", (60, 40), "cyan").save(stream, format="PNG")
    uploaded = client.post(
        "/api/books/" + a["id"] + "/image",
        files={"file": ("book.png", stream.getvalue(), "image/png")},
        headers={"X-Saly-Request": "1"},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset = uploaded.json()["id"]
    data = book(cover_asset_id=asset)
    assert (
        client.patch(
            "/api/books/" + b["id"], json={"data": data, "base_revision": 1, "confirm": True}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/books/" + a["id"], json={"data": data, "base_revision": 1, "confirm": True}
        ).status_code
        == 200
    )
    assert (
        client.delete(
            "/api/books/" + a["id"] + "/assets/" + asset + "?confirm=true",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 409
    )
    client.cookies.clear()
    assert client.get("/api/books").status_code == 401
    assert client.get("/api/private-assets/" + asset).status_code == 401


def test_initial_biology_is_valid_original_draft_idempotent_and_not_resurrected(client):
    from backend.biology import ensure_biology_draft
    from backend.library import Book

    ensure_biology_draft()
    ensure_biology_draft()
    books = store.all_records("books")
    assert len(books) == 1 and not books[0].get("published_version_id")
    data = Book.model_validate(books[0]["draft"])
    assert data.publication_status == "draft" and len(data.chapters) == 8
    assert len([p for c in data.chapters for p in c.pages]) == 9
    blocks = {block.type for c in data.chapters for p in c.pages for block in p.blocks}
    assert {"text", "quiz", "dnaLab", "ecologyLab", "cellViewer", "microscope"} <= blocks
    assert not data.chapters[4].pages and not data.chapters[6].pages
    assert all(s.checked_on is None for c in data.chapters for p in c.pages for s in p.sources)
    assert (
        client.delete(
            "/api/books/" + books[0]["id"] + "?base_revision=1&confirm=true",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    ensure_biology_draft()
    assert not store.all_records("books")
