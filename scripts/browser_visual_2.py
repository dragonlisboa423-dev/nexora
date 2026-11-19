"""SALY 2.0: actual navigation/graphics/purchases/reader/PWA; chat transport controlled."""

import hashlib
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from browser_navigation import go
from browser_support import PASSWORD, test_server
from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright


def save_purchase(context, base, name, price, status="purchased", quantity=1):
    result = context.request.post(
        base + "/api/purchases",
        data={
            "data": {
                "product": name,
                "price_cents": price,
                "quantity": quantity,
                "purchased_on": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d"),
                "category": "livros" if "Livro" in name else "estudo",
                "status": status,
            },
            "confirm": True,
        },
    )
    assert result.ok, result.text()
    return result.json()


def swipe(page, locator):
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    assert box
    y = max(130, min(600, box["y"] + 120))
    x = min(330, box["x"] + box["width"] * 0.82)
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    cdp.send(
        "Input.dispatchTouchEvent",
        {"type": "touchMove", "touchPoints": [{"x": x - 100, "y": y + 3}]},
    )
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    cdp.detach()


with test_server(port=8013) as base, sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=[
            "--no-sandbox",
            "--enable-unsafe-swiftshader",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000},
        has_touch=True,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    context.add_init_script(
        "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;"
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    expect(
        page.get_by_role("navigation", name="Áreas principais", exact=True).get_by_role("link")
    ).to_have_count(4)
    assert page.get_by_role(
        "navigation", name="Áreas principais", exact=True
    ).inner_text().splitlines() == ["Conversa", "Conhecimento", "Mídia", "Rotina"]
    assert not page.get_by_role("link", name="Ferramentas e integrações", exact=True).count()
    assert not page.get_by_role("textbox", name=re.compile("JSON")).count()
    core = page.locator(".botanical-core")
    expect(core).to_have_attribute("data-core-renderer", "webgl")
    page.wait_for_function('Number(document.querySelector(".botanical-core").dataset.frames)>1')
    anatomy = core.evaluate("node=>({...node.dataset})")
    assert int(anatomy["triangles"]) < 40000
    page.screenshot(path="/tmp/saly-2-conversation-desktop.png", full_page=True)
    metrics = page.evaluate(
        """()=>new Promise(resolve=>{let frames=0;const start=performance.now();function tick(){frames++;if(performance.now()-start<2500)requestAnimationFrame(tick);else resolve({frames,elapsed_ms:performance.now()-start,fps:frames/((performance.now()-start)/1000),js_bytes:performance.getEntriesByType('resource').filter(r=>/\\.(js|mjs)(\\?|$)/.test(r.name)).reduce((s,r)=>s+r.encodedBodySize,0)});}requestAnimationFrame(tick);})"""
    )
    page.get_by_role("button", name="Ativar microfone", exact=True).click()
    page.get_by_role("button", name="Parar microfone", exact=True).wait_for()
    expect(core).to_have_class(re.compile("listening"))
    page.get_by_role("button", name="Parar microfone", exact=True).click()
    page.get_by_role("button", name="Fechar aviso", exact=True).click()
    page.get_by_role("button", name="Histórico de conversas", exact=True).click()
    expect(page.get_by_role("dialog", name="Histórico de conversas")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog", name="Histórico de conversas")).not_to_be_visible()
    # Actual IntersectionObserver/R3F pause and genuine context-loss fallback.
    page.evaluate(
        "() => {const spacer=document.createElement('div');spacer.id='visibility-probe';spacer.style.height='1800px';document.body.append(spacer);window.scrollTo(0,document.body.scrollHeight);}"
    )
    expect(core).to_have_attribute("data-core-active", "false")
    stopped = core.get_attribute("data-frames")
    page.wait_for_timeout(500)
    assert core.get_attribute("data-frames") == stopped
    page.evaluate(
        "() => {window.scrollTo(0,0);document.getElementById('visibility-probe').remove();}"
    )
    expect(core).to_have_attribute("data-core-active", "true")
    core.locator("canvas").evaluate(
        "canvas=>canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext()"
    )
    expect(core).to_have_attribute("data-core-renderer", "css-fallback")
    page.reload()
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    go(page, "Memórias")
    page.get_by_role("button", name="+ Nova memória", exact=True).click()
    page.get_by_label("Conteúdo", exact=True).fill("MEMÓRIA PRESERVADA SALY 2")
    page.get_by_role("button", name="Salvar", exact=True).click()
    page.get_by_text("MEMÓRIA PRESERVADA SALY 2", exact=True).wait_for()
    page.get_by_role("navigation", name="Áreas principais", exact=True).get_by_role(
        "link", name="Conhecimento", exact=True
    ).click()
    page.get_by_role("heading", name="Centro Memorial", exact=True).wait_for()
    page.screenshot(path="/tmp/saly-2-knowledge-desktop.png", full_page=True)

    purchased = save_purchase(context, base, "Livro botânico de teste", 4590, quantity=2)
    save_purchase(context, base, "Microscópio de teste", 14900, "delivered")
    save_purchase(context, base, "Desejo de teste", 58000, "wishlist")
    month = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m")
    assert context.request.put(
        base + "/api/purchases-budget",
        data={"month": month, "amount_cents": 50000, "confirm": True},
    ).ok
    go(page, "Compras")
    region = page.get_by_role("region", name="Visão financeira dos registros")
    expect(region).to_contain_text("240,80")
    expect(region).to_contain_text("259,20")
    card = page.locator("article.product-card").filter(
        has=page.get_by_role("heading", name="Livro botânico de teste", exact=True)
    )
    card.get_by_role("button", name="Adicionar foto de Livro botânico de teste", exact=True).click()
    picture = Image.new("RGB", (500, 360), "#c9cdb2")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((130, 35, 380, 330), fill="#344b2c")
    draw.line((148, 35, 148, 330), fill="#8ba06a", width=3)
    draw.text((177, 130), "BOTANICA", fill="#dee8c4")
    raw = io.BytesIO()
    picture.save(raw, format="PNG")
    card.get_by_label("Foto de Livro botânico de teste", exact=True).set_input_files(
        {"name": "livro.png", "mimeType": "image/png", "buffer": raw.getvalue()}
    )
    card.get_by_role("button", name="Guardar foto do produto", exact=True).click()
    card.get_by_alt_text("Foto de Livro botânico de teste", exact=True).wait_for()
    page.get_by_role("button", name="Nova meta", exact=True).click()
    page.get_by_label("Nome da meta", exact=True).fill("Minha biblioteca")
    page.get_by_label("Valor da meta em reais", exact=True).fill("1000,00")
    page.get_by_label("Valor já reservado em reais", exact=True).fill("250,00")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Guardar meta", exact=True).click()
    page.get_by_role("progressbar", name="Progresso da meta Minha biblioteca").wait_for()
    page.reload()
    page.get_by_role("progressbar", name="Progresso da meta Minha biblioteca").wait_for()
    card.get_by_alt_text("Foto de Livro botânico de teste", exact=True).wait_for()
    page.screenshot(path="/tmp/saly-2-purchases-desktop.png", full_page=True)
    summary = context.request.get(base + "/api/purchases-summary?month=" + month).json()
    assert summary["total_cents"] == 24080 and summary["remaining_cents"] == 25920

    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.screenshot(path="/tmp/saly-2-purchases-mobile.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    go(page, "Biblioteca")
    catalog = context.request.get(base + "/api/books").json()
    biology = next(book for book in catalog if book["subject"] == "Biologia")
    before = context.request.get(base + f"/api/books/{biology['id']}").json()
    fingerprint = hashlib.sha256(
        json.dumps(before["chapters"], sort_keys=True).encode()
    ).hexdigest()
    page.get_by_role("button", name="Ler " + biology["title"], exact=True).click()
    reader = page.get_by_label("Leitor de livro", exact=True)
    expect(reader.locator("article.book-leaf")).to_have_count(2)
    page.get_by_role("button", name="Marcar página 1", exact=True).click()
    page.get_by_role("button", name="Remover marcador 1", exact=True).wait_for()
    page.screenshot(path="/tmp/saly-2-book-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(reader.locator("article.book-leaf")).to_have_count(1)
    swipe(page, reader)
    expected = before["chapters"][0]["pages"][1]["id"]
    for _ in range(150):
        progress = context.request.get(base + f"/api/books/{biology['id']}/progress").json()
        if progress.get("current_page_id") == expected:
            break
        page.wait_for_timeout(20)
    assert progress.get("current_page_id") == expected, progress
    assert before["chapters"][0]["pages"][0]["id"] in progress["bookmarks"]
    page.get_by_role("navigation", name="Navegação móvel", exact=True).get_by_role(
        "link", name="Rotina", exact=True
    ).click()
    page.get_by_role("heading", name="Espaço para o seu dia.", exact=True).wait_for()
    go(page, "Biblioteca")
    page.get_by_role("button", name="Ler " + biology["title"], exact=True).click()
    expect(reader).to_contain_text(before["chapters"][0]["pages"][1]["title"])
    page.emulate_media(reduced_motion="reduce")
    assert (
        reader.locator("article.book-leaf").first.evaluate(
            "node=>getComputedStyle(node).animationName"
        )
        == "none"
    )
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.screenshot(path="/tmp/saly-2-book-mobile.png", full_page=True)
    after = context.request.get(base + f"/api/books/{biology['id']}").json()
    assert (
        hashlib.sha256(json.dumps(after["chapters"], sort_keys=True).encode()).hexdigest()
        == fingerprint
    )

    go(page, "Estúdio Multimídia")
    page.get_by_role("tab", name="Imagem", exact=True).wait_for()
    expect(
        page.get_by_role("button", name="Geração de imagem não conectada", exact=True)
    ).to_be_disabled()
    page.get_by_role("tab", name="Vídeo", exact=True).click()
    expect(
        page.get_by_text("Geração de cenas por IA não está conectada.", exact=True)
    ).to_be_visible()
    page.screenshot(path="/tmp/saly-2-media-mobile.png", full_page=True)
    page.get_by_role("tab", name="Galeria", exact=True).focus()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("tab", name="Produções", exact=True)).to_be_focused()
    expect(page.get_by_role("tab", name="Produções", exact=True)).to_have_attribute(
        "aria-selected", "true"
    )
    page.get_by_role("navigation", name="Navegação móvel", exact=True).get_by_role(
        "link", name="Conversa", exact=True
    ).click()
    expect(core).to_have_attribute("data-motion", "reduced")
    page.screenshot(path="/tmp/saly-2-conversation-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    go(page, "Configurações")
    settings = context.request.get(base + "/api/settings").json()
    settings["graphics"] = "2d"
    assert context.request.put(base + "/api/settings", data=settings).ok
    page.goto(base)
    expect(core).to_have_attribute("data-core-renderer", "css-fallback")
    expect(core.locator(".restored-fluid-flat")).to_be_visible()
    assert (
        context.request.get(base + "/api/memories").json()[0]["content"]
        == "MEMÓRIA PRESERVADA SALY 2"
    )
    assert not errors, errors
    result = {
        "result": "passed",
        "primary_areas": 4,
        "graphics": anatomy,
        "performance": metrics,
        "flows": [
            "WebGL botanical tissues, live microphone state, viewport pause and context-loss fallback",
            "native history drawer",
            "preserved memory",
            "private product photo, actual expense charts and saved goal",
            "two/single-page biology reading, touch swipe, bookmark, persistent progress, unchanged source content",
            "disabled unconfigured generation, gallery/productions keyboard tabs",
            "mobile no horizontal overflow",
            "reduced motion and lightweight vector fallback",
        ],
        "page_errors": errors,
        "android_physical": False,
        "provider_requests": 0,
    }
    Path("/tmp/saly-2-functional-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(json.dumps(result, ensure_ascii=False))
    browser.close()
