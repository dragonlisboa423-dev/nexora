"""Actual image edit, CPU montage, playable/downloadable MP4; no provider calls."""

import hashlib
import io
import json
import os
from pathlib import Path

from browser_navigation import go
from browser_support import PASSWORD, test_server
from PIL import Image
from playwright.sync_api import expect, sync_playwright

with test_server(port=8008) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    go(page, "Estúdio Multimídia")
    expect(
        page.get_by_role("button", name="Geração de imagem não conectada", exact=True)
    ).to_be_disabled()
    page.get_by_role("tab", name="Galeria", exact=True).click()
    stream = io.BytesIO()
    Image.new("RGB", (160, 90), "green").save(stream, format="PNG")
    page.get_by_label("Enviar mídia privada", exact=True).set_input_files(
        {"name": "image.png", "mimeType": "image/png", "buffer": stream.getvalue()}
    )
    page.get_by_role("img", name="Imagem privada", exact=False).wait_for()
    assets = context.request.get(base + "/api/media/assets").json()
    asset = assets[0]
    page.get_by_role("tab", name="Imagem", exact=True).click()
    page.get_by_label("Imagem a editar", exact=True).select_option(asset["id"])
    page.get_by_label("Rotação horária", exact=True).select_option("90")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Aplicar edição local", exact=True).click()
    page.get_by_role("tab", name="Galeria", exact=True).click()
    expect(page.get_by_role("img", name="Imagem privada", exact=False)).to_have_count(2)
    page.get_by_role("button", name="Adicionar cena " + asset["id"][:8], exact=True).click()
    page.get_by_role("tab", name="Vídeo", exact=True).click()
    page.get_by_label("Duração em segundos", exact=True).fill("2")
    page.get_by_label("Legenda desta cena", exact=True).fill("SALY · montagem real")
    page.get_by_label("Transição do vídeo", exact=True).select_option("fade")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Exportar montagem local", exact=True).click()
    page.get_by_role("tab", name="Produções", exact=True).click()
    page.get_by_role(
        "heading", name="Montagem local · Concluída com arquivo validado", exact=True
    ).wait_for(timeout=30000)
    job = context.request.get(base + "/api/media/jobs").json()[0]
    assert job["status"] == "completed"
    with page.expect_download() as downloaded:
        page.get_by_role("link", name="Baixar resultado verificado", exact=True).click()
    raw = Path(downloaded.value.path()).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == job["result_sha256"]
    Path("/tmp/saly-studio-montage.mp4").write_bytes(raw)
    page.get_by_role("tab", name="Galeria", exact=True).click()
    video = page.locator(".asset-gallery video").first
    video.wait_for()
    video.evaluate("(video)=>video.play()")
    page.wait_for_function('document.querySelector(".asset-gallery video").currentTime>0')
    page.reload()
    page.get_by_role("tab", name="Produções", exact=True).click()
    page.get_by_role(
        "heading", name="Montagem local · Concluída com arquivo validado", exact=True
    ).wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.wait_for_function(
        "document.querySelector('.sidebar').getBoundingClientRect().right <= 0.5"
    )
    page.screenshot(path="/tmp/saly-studio-mobile.png", full_page=True)
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "unconfigured generation disabled",
                    "real private image upload/rotation",
                    "FFmpeg caption/fade montage",
                    "download checksum",
                    "native MP4 playback currentTime",
                    "persisted history",
                    "mobile",
                ],
                "provider_requests": 0,
                "page_errors": errors,
            }
        )
    )
    context.close()
    browser.close()
