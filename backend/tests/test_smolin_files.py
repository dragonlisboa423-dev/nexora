import hashlib
import io
import shutil
import struct
import time
import wave
import zipfile

import pytest
from PIL import Image, ImageDraw, ImageFont

from backend import storage as store
from backend.smolin import service


def send(client, raw, name):
    result = client.post(
        "/api/knowledge", files={"file": (name, raw)}, headers={"X-Saly-Request": "1"}
    )
    assert result.status_code == 200, result.text
    return result.json()


def finished(client, key):
    for _ in range(400):
        doc = client.get("/api/knowledge/" + key).json()
        if doc["status"] not in {"queued", "processing"}:
            return doc
        time.sleep(0.04)
    pytest.fail("Arquivo não terminou de processar")


def package(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def test_any_binary_is_preserved_downloadable_but_not_executed_or_indexed(client):
    raw = b"MZ\x00\x01binary example\xff"
    result = send(client, raw, "programa.exe")
    doc = client.get("/api/knowledge/" + result["id"]).json()
    assert doc["status"] == "stored_only" and not doc["chunks"]
    original = client.get("/api/knowledge/" + doc["id"] + "/original?download=true")
    assert original.content == raw
    assert original.headers["content-disposition"].startswith("attachment;")
    assert original.headers["x-content-type-options"] == "nosniff"
    assert doc["sha256"] == hashlib.sha256(raw).hexdigest()
    assert not client.get("/api/knowledge/search?q=binary").json()
    client.cookies.clear()
    assert client.get("/api/knowledge/" + doc["id"] + "/original?download=true").status_code == 401


def test_range_downloads_valid_invalid_suffix_and_original_integrity(client):
    raw = b"0123456789abcdef"
    key = send(client, raw, "amostra.bin")["id"]
    url = "/api/knowledge/" + key + "/original"
    selected = client.get(url, headers={"Range": "bytes=2-6"})
    assert selected.status_code == 206 and selected.content == b"23456"
    assert selected.headers["content-range"] == "bytes 2-6/16"
    assert client.get(url, headers={"Range": "bytes=-4"}).content == b"cdef"
    assert client.get(url, headers={"Range": "bytes=40-50"}).status_code == 416
    assert client.get(url, headers={"Range": "bytes=0-1,4-5"}).status_code == 416
    assert client.get(url).content == raw


def test_small_chunks_are_idempotent_and_complete_only_after_all_bytes(client):
    raw = "Biologia em blocos. Células e genética.".encode()
    record = client.post(
        "/api/knowledge/uploads", json={"name": "pasta/nota.txt", "size": len(raw)}
    ).json()
    key = record["id"]
    url = "/api/knowledge/uploads/" + key
    headers = {"Content-Type": "application/octet-stream", "X-Saly-Request": "1"}
    assert client.put(url + "?offset=0", content=raw[:12], headers=headers).json()["offset"] == 12
    assert client.put(url + "?offset=0", content=raw[:12], headers=headers).json()["duplicate"]
    assert client.put(url + "?offset=0", content=b"x" * 12, headers=headers).status_code == 409
    assert client.post(url + "/complete", json={}).status_code == 409
    assert client.put(url + "?offset=12", content=raw[12:], headers=headers).status_code == 200
    uploaded = client.post(url + "/complete", json={})
    assert uploaded.status_code == 200, uploaded.text
    doc = finished(client, uploaded.json()["id"])
    assert doc["status"] == "ready" and doc["name"] == "nota.txt"
    assert client.get("/api/knowledge/" + doc["id"] + "/original?download=true").content == raw
    assert not store.all_records("smolin_uploads")


def test_upload_limits_precede_chunks_and_cancel_cleans_partial_file(client, monkeypatch):
    monkeypatch.setenv("SALY_SMOLIN_MAX_UPLOAD_MB", "1")
    assert (
        client.post(
            "/api/knowledge/uploads", json={"name": "large.pdf", "size": 2 * 1024 * 1024}
        ).status_code
        == 413
    )
    record = client.post("/api/knowledge/uploads", json={"name": "x.bin", "size": 30}).json()
    assert (
        client.delete(
            "/api/knowledge/uploads/" + record["id"], headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert not (store.DATA / "smolin-uploads" / (record["id"] + ".part")).exists()
    client.cookies.clear()
    assert (
        client.post("/api/knowledge/uploads", json={"name": "x.bin", "size": 1}).status_code == 401
    )


def test_structured_text_office_epub_and_archive_are_real_extractions(client):
    samples = [
        ("dados.csv", b"gene,funcao\nDNA,hereditariedade", "hereditariedade"),
        ("dados.json", b'{"conceito":"mitocondria"}', "mitocondria"),
        ("pagina.html", b"<h1>Ribossomos</h1><script>DO_NOT_INDEX</script>", "Ribossomos"),
        ("texto.txt", "Cloroplastos e fotossíntese".encode("utf-16"), "fotossíntese"),
        (
            "livro.docx",
            package({"word/document.xml": "<document><p><t>Membrana celular</t></p></document>"}),
            "Membrana",
        ),
        (
            "slides.pptx",
            package({"ppt/slides/slide1.xml": "<slide><p><t>Mitose celular</t></p></slide>"}),
            "Mitose",
        ),
        (
            "planilha.xlsx",
            package(
                {
                    "xl/sharedStrings.xml": "<sst><si><t>ATP energia</t></si></sst>",
                    "xl/worksheets/sheet1.xml": '<worksheet><row><c t="s"><v>0</v></c></row></worksheet>',
                }
            ),
            "ATP",
        ),
        (
            "livro.epub",
            package({"chapter.xhtml": "<html><p>Metabolismo celular</p></html>"}),
            "Metabolismo",
        ),
        (
            "notas.odt",
            package({"content.xml": "<document><p>Ecossistema</p></document>"}),
            "Ecossistema",
        ),
        ("pacote.zip", package({"referencia.txt": "Conteúdo interno indexado"}), "Conteúdo interno indexado"),
    ]
    for name, raw, expected in samples:
        doc = finished(client, send(client, raw, name)["id"])
        assert doc["status"] == "ready", (name, doc)
        assert expected in doc["content"]
        assert "DO_NOT_INDEX" not in doc["content"]
        assert client.get("/api/knowledge/" + doc["id"] + "/original").content == raw
    assert client.get("/api/knowledge/search?q=Mitose").json()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg real não instalado")
def test_audio_real_metadata_player_ranges_and_honest_transcription_dependency(client):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as target:
        target.setparams((1, 2, 16000, 0, "NONE", "none"))
        target.writeframes(struct.pack("<h", 0) * 16000)
    doc = finished(client, send(client, stream.getvalue(), "audio.wav")["id"])
    assert doc["kind"] == "audio" and doc["status"] == "transcription_required"
    assert abs(doc["media_info"]["duration_seconds"] - 1) < 0.01 and not doc["content"]
    capability = client.get("/api/knowledge/capabilities").json()["transcription"]
    if not capability["available"]:
        assert (
            client.post("/api/knowledge/" + doc["id"] + "/transcribe", json={}).status_code == 503
        )
    assert (
        client.get(
            "/api/knowledge/" + doc["id"] + "/original", headers={"Range": "bytes=0-43"}
        ).status_code
        == 206
    )


@pytest.mark.skipif(not shutil.which("tesseract"), reason="OCR real não instalado")
def test_image_real_local_ocr(client):
    image = Image.new("RGB", (1200, 240), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 65)
    draw.text((30, 60), "BIOLOGY CELL", font=font, fill="black")
    raw = io.BytesIO()
    image.save(raw, format="PNG")
    doc = finished(client, send(client, raw.getvalue(), "imagem.png")["id"])
    assert doc["status"] == "ready" and "BIOLOGY" in doc["content"].upper()
    assert client.get("/api/knowledge/search?q=BIOLOGY").json()


def test_zip_xml_entity_rejected_original_kept(client):
    raw = package(
        {"word/document.xml": '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><p>&e;</p>'}
    )
    doc = finished(client, send(client, raw, "unsafe.docx")["id"])
    assert doc["status"] == "failed" and not doc["content"]
    assert client.get("/api/knowledge/" + doc["id"] + "/original?download=true").content == raw


def test_pdf_reading_position_private_and_persistent(client):
    key = send(client, b"%PDF-1.7 malformed for download test", "original.pdf")["id"]
    assert client.get("/api/knowledge/" + key + "/reading-position").json() == {"page": 1}
    assert (
        client.put("/api/knowledge/" + key + "/reading-position", json={"page": 7}).status_code
        == 200
    )
    assert client.get("/api/knowledge/" + key + "/reading-position").json() == {"page": 7}
    client.cookies.clear()
    assert client.get("/api/knowledge/" + key + "/reading-position").status_code == 401


@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("tesseract")), reason="FFmpeg e OCR reais exigidos"
)
def test_video_real_frame_ocr_time_citations_and_mp3(client, tmp_path):
    import subprocess

    video = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=720x240:d=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-vf",
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text=BIOLOGY CELL:fontcolor=black:fontsize=60:x=25:y=80",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(video),
        ],
        check=True,
        capture_output=True,
        timeout=20,
    )
    doc = finished(client, send(client, video.read_bytes(), "aula.mp4")["id"])
    assert doc["kind"] == "video" and doc["status"] == "partial", doc
    assert "BIOLOGY" in doc["content"].upper() and not doc["transcribed"]
    citation = next(
        r for r in client.get("/api/knowledge/search?q=BIOLOGY").json() if r["id"] == doc["id"]
    )
    assert (
        citation["method"] == "sampled_frame_ocr"
        and citation["start_seconds"] >= 0
        and "#t=" in citation["url"]
    )
    mp3 = tmp_path / "audio.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-c:a", "libmp3lame", str(mp3)],
        check=True,
        capture_output=True,
        timeout=15,
    )
    audio = finished(client, send(client, mp3.read_bytes(), "som.mp3")["id"])
    assert (
        audio["kind"] == "audio"
        and audio["mime"] == "audio/mpeg"
        and audio["status"] == "transcription_required"
    )
    assert (
        client.get("/api/knowledge/" + doc["id"] + "/original?download=true").content
        == video.read_bytes()
    )


def test_original_and_metadata_rollback_together_on_storage_failure(client):
    from sqlalchemy import event
    from sqlalchemy.exc import SQLAlchemyError

    def fail_original(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO document_originals"):
            raise SQLAlchemyError("Controlled storage failure")

    event.listen(store.engine, "before_cursor_execute", fail_original)
    try:
        with pytest.raises(SQLAlchemyError):
            service.upload(b"Atomic original text", "atomic.txt")
    finally:
        event.remove(store.engine, "before_cursor_execute", fail_original)
    assert not store.all_records("documents") and not store.all_records("document_jobs")
    assert not client.get("/api/sync/bootstrap").json()["entities"]["documents"]
