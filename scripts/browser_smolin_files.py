"""Real Smolin originals, chunked upload and original PDF canvas/text/book navigation."""

import hashlib
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from browser_support import PASSWORD, test_server
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def pdf_original():
    writer = PdfWriter()
    for number in range(1, 5):
        page = writer.add_blank_page(width=320, height=480)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = DecodedStreamObject()
        content.set_data(
            f"1 0 0 rg 30 180 180 100 re f 0 0 0 rg BT /F1 20 Tf 30 420 Td (PDF ORIGINAL {number}) Tj ET".encode()
        )
        page[NameObject("/Contents")] = writer._add_object(content)
    writer.add_outline_item("Inicio original", 0)
    writer.add_outline_item("Segunda parte", 2)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


with test_server(port=8010) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("link", name="Centro Smolin", exact=True).click()

    def proxy_error(route):
        if route.request.method == "POST":
            route.fulfill(status=413, content_type="text/html", body="<html>proxy failure</html>")
        else:
            route.continue_()

    page.route("**/api/knowledge", proxy_error)
    page.get_by_label("Importar documentos", exact=True).set_input_files(
        {"name": "proxy.csv", "mimeType": "text/csv", "buffer": b"gene,value"}
    )
    page.get_by_text("HTTP 413:", exact=False).wait_for()
    assert "Unexpected token" not in page.locator("body").inner_text()
    page.unroute("**/api/knowledge", proxy_error)
    raw = b"\x00NEXORA_RAW\xff" * 500000
    page.get_by_label("Importar documentos", exact=True).set_input_files(
        {"name": "arquivo-grande.bin", "mimeType": "application/octet-stream", "buffer": raw}
    )
    card = page.locator("article.card").filter(
        has=page.get_by_role("heading", name="arquivo-grande.bin", exact=True)
    )
    card.wait_for(timeout=30000)
    with page.expect_download() as downloading:
        card.get_by_role("link", name="Baixar original", exact=True).click()
    assert Path(downloading.value.path()).read_bytes() == raw
    uploaded = context.request.get(base + "/api/knowledge").json()[0]
    assert uploaded["status"] == "stored_only"
    original = pdf_original()
    page.get_by_label("Importar documentos", exact=True).set_input_files(
        {"name": "livro-original.pdf", "mimeType": "application/pdf", "buffer": original}
    )
    pdfcard = page.locator("article.card").filter(
        has=page.get_by_role("heading", name="livro-original.pdf", exact=True)
    )
    pdfcard.wait_for()
    pdfcard.get_by_role("link", name="Ler PDF como livro", exact=True).click()
    page.get_by_role("status").filter(has_text="Página 1 de 4").wait_for()
    expect(page.locator(".pdf-leaf")).to_have_count(2)
    page.locator(".textLayer").first.get_by_text("PDF ORIGINAL 1", exact=True).wait_for()
    canvas = page.get_by_label("Imagem original da página 1", exact=True)
    red = canvas.evaluate(
        """canvas=>{const rgba=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let total=0;for(let i=0;i<rgba.length;i+=4)if(rgba[i]>200&&rgba[i+1]<80&&rgba[i+2]<80)total++;return total;}"""
    )
    assert red > 1000, "Original red diagram was not rendered"
    page.get_by_role("button", name="Próxima página do PDF", exact=True).click()
    page.get_by_role("status").filter(has_text="Página 3 de 4").wait_for()
    page.get_by_role("button", name="Mostrar texto acessível da página atual", exact=True).click()
    expect(page.get_by_role("region", name="Texto da página original", exact=True)).to_contain_text(
        "PDF ORIGINAL 3"
    )
    key = next(
        d["id"]
        for d in context.request.get(base + "/api/knowledge").json()
        if d["name"] == "livro-original.pdf"
    )
    for attempt in range(100):
        if (
            context.request.get(base + "/api/knowledge/" + key + "/reading-position").json()["page"]
            == 3
        ):
            break
        page.wait_for_timeout(50)
    else:
        raise AssertionError("Reading position not persisted")
    page.get_by_role("link", name="← Voltar ao Centro Smolin", exact=True).click()
    page.get_by_role("link", name="Ler PDF como livro", exact=True).click()
    page.get_by_role("status").filter(has_text="Página 3 de 4").wait_for()
    page.get_by_label("Zoom do PDF", exact=True).fill("1.5")
    page.get_by_role("button", name="Girar páginas", exact=True).click()
    page.get_by_label("Desativar animação de virada", exact=True).check()
    with page.expect_download() as downloading:
        page.get_by_role("link", name="Baixar PDF original", exact=True).click()
    assert (
        hashlib.sha256(Path(downloading.value.path()).read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right<=0.5")
    expect(page.locator(".pdf-leaf")).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.screenshot(path="/tmp/saly-pdf-book-mobile.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("link", name="← Voltar ao Centro Smolin", exact=True).click()
    with tempfile.TemporaryDirectory(prefix="saly-browser-media-") as directory:
        video = Path(directory) / "sample.mp4"
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
            capture_output=True,
            check=True,
            timeout=20,
        )
        mp3 = Path(directory) / "sample.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(video),
                "-vn",
                "-c:a",
                "libmp3lame",
                str(mp3),
            ],
            capture_output=True,
            check=True,
            timeout=15,
        )
        page.get_by_label("Importar documentos", exact=True).set_input_files([str(video), str(mp3)])
        video_card = page.locator("article.card").filter(
            has=page.get_by_role("heading", name="sample.mp4", exact=True)
        )
        audio_card = page.locator("article.card").filter(
            has=page.get_by_role("heading", name="sample.mp3", exact=True)
        )
        video_card.get_by_text("Foram amostrados", exact=False).wait_for(timeout=30000)
        audio_card.get_by_text("Fala ainda não transcrita.", exact=False).wait_for()
        video_card.locator("video").evaluate("video=>{video.muted=true;return video.play();}")
        page.wait_for_function('document.querySelector(".smolin-video").currentTime>0')
        audio_card.locator("audio").evaluate("audio=>{audio.muted=true;return audio.play();}")
        page.wait_for_function('document.querySelector("audio").currentTime>0')
        transcription = context.request.get(base + "/api/knowledge/capabilities").json()[
            "transcription"
        ]
        if not transcription["available"]:
            expect(
                audio_card.get_by_role("button", name="Transcrever fala localmente", exact=True)
            ).to_be_disabled()
        page.get_by_label("Pesquisar Centro Smolin", exact=True).fill("BIOLOGY")
        page.get_by_role("button", name="Pesquisar", exact=True).click()
        page.get_by_role("link", name="sample.mp4 ·", exact=False).first.wait_for()
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "HTML proxy error explained",
                    "binary original via 2MB chunks/download equality",
                    "PDF original red diagram rendered on canvas",
                    "selectable PDF text",
                    "double/single pages and turn",
                    "zoom/rotation/reduced animation",
                    "saved reading position",
                    "real MP4/MP3 playback and video frame OCR search",
                    "missing speech model reported without fake transcription",
                    "original checksum unchanged",
                    "mobile",
                ],
                "page_errors": errors,
            }
        )
    )
    context.close()
    browser.close()
