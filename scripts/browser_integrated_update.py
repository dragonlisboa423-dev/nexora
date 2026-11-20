"""Real UI verification with a disposable database, never real user data."""

import io
import json
import time
import zipfile

from browser_support import PASSWORD, test_server
from PIL import Image
from playwright.sync_api import expect, sync_playwright

with test_server(port=8015) as base, sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium",
        headless=True,
        args=["--no-sandbox", "--enable-unsafe-swiftshader"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    selector = page.get_by_label("Modelo da conversa", exact=True)
    expect(selector).to_have_value("qwen2.5:3b")
    selector.select_option("remote")
    expect(selector).to_be_enabled()
    expect(selector).to_have_value("remote")
    page.reload()
    expect(page.get_by_label("Modelo da conversa", exact=True)).to_have_value("remote")
    page.get_by_label("Modelo da conversa", exact=True).select_option("qwen2.5:3b")
    expect(page.get_by_label("Modelo da conversa", exact=True)).to_be_enabled()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("biologia/notas.txt", "Clorofila captura energia da luz.")
        z.writestr("biologia/amostra.json", '{"tipo":"planta"}')
    response = page.request.post(
        base + "/api/knowledge",
        multipart={
            "file": {
                "name": "acervo.zip",
                "mimeType": "application/zip",
                "buffer": archive.getvalue(),
            }
        },
        headers={"X-Saly-Request": "1"},
    )
    assert response.ok, response.text()
    key = response.json()["id"]
    for _ in range(100):
        doc = page.request.get(base + "/api/knowledge/" + key).json()
        if doc["status"] not in ("queued", "processing"):
            break
        time.sleep(0.1)
    assert doc["status"] == "ready", doc
    page.goto(base + "/knowledge/documents")
    tree = page.locator(".archive-tree")
    tree.locator("> summary").click()
    tree.get_by_text("biologia/", exact=True).click()
    expect(tree.get_by_text("notas.txt", exact=False)).to_be_visible()
    link = tree.get_by_role("link", name="Abrir", exact=True).first
    assert "/entries/0/original" in link.get_attribute("href")
    actual = page.request.get(base + link.get_attribute("href"))
    assert actual.text() == "Clorofila captura energia da luz."
    prefs = page.request.get(base + "/api/settings").json()
    prefs["graphics"] = "high"
    assert page.request.put(
        base + "/api/settings",
        data=json.dumps(prefs),
        headers={"Content-Type": "application/json", "X-Saly-Request": "1"},
    ).ok
    page.goto(base + "/settings/system")
    page.get_by_text("Pulsação do núcleo", exact=True).click()
    page.get_by_label("Intensidade da pulsação", exact=True).fill("0.9")
    assert page.evaluate("JSON.parse(localStorage.getItem('saly-core-motion')).intensity") == 0.9
    page.goto(base)
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    expect(page.locator(".core")).to_have_attribute("data-bloom", "enabled")
    screenshot = page.screenshot(path="/tmp/saly-integrated-high.png", full_page=True)
    rendered = Image.open(io.BytesIO(screenshot)).convert("RGB")
    bounds = page.locator("canvas").bounding_box()
    x, y = int(bounds["x"]), int(bounds["y"])
    # Canvas corner must blend into its actual adjacent page background, not a black rectangle.
    inside = rendered.getpixel((x + 4, y + 4))
    outside = rendered.getpixel((x - 4, y + 4))
    assert max(abs(a - b) for a, b in zip(inside, outside, strict=True)) < 7, (inside, outside)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "flows": [
                    "persisted local selector without auto-download",
                    "real ZIP tree/private entry bytes",
                    "pulse slider persisted on device",
                    "actual high-quality WebGL bloom",
                    "mobile width",
                ],
                "page_errors": errors,
            }
        )
    )
    browser.close()
