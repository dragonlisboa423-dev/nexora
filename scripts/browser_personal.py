"""Purchases and drawers with real persistence/files, no external provider."""

import io
import json
import os

from browser_support import PASSWORD, test_server
from PIL import Image
from playwright.sync_api import expect, sync_playwright

with test_server(port=8005) as base, sync_playwright() as playwright:
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
    page.get_by_role("link", name="Compras", exact=True).click()
    page.get_by_role("button", name="+ Nova compra", exact=True).click()
    page.get_by_label("Produto", exact=True).fill("Microscópio E2E")
    page.get_by_label("Preço unitário em reais", exact=True).fill("123,45")
    page.get_by_label("Quantidade", exact=True).fill("2")
    page.get_by_label("Frete em reais", exact=True).fill("9,99")
    page.get_by_label("Desconto em reais", exact=True).fill("1,00")
    page.get_by_label("Entrega prevista", exact=True).fill("2026-12-20")
    page.get_by_role("button", name="Conferir total", exact=True).click()
    expect(page.get_by_role("region", name="Total conferido")).to_contain_text("255,89")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Confirmar compra", exact=True).click()
    page.get_by_role("heading", name="Microscópio E2E", exact=True).wait_for()
    page.get_by_label("Orçamento em reais", exact=True).fill("300,00")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Salvar orçamento", exact=True).click()
    page.get_by_text("Saldo:", exact=False).filter(has_text="44,11").wait_for()
    page.get_by_text("Comprovante privado · Microscópio E2E", exact=True).click()
    stream = io.BytesIO()
    Image.new("RGB", (70, 40), "green").save(stream, format="PNG")
    page.get_by_label("Selecionar comprovante", exact=True).set_input_files(
        {"name": "receipt.png", "mimeType": "image/png", "buffer": stream.getvalue()}
    )
    expect(page.get_by_alt_text("Prévia do arquivo selecionado", exact=True)).to_be_visible()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar imagem", exact=True).click()
    page.get_by_role("link", name="Abrir comprovante", exact=True).wait_for()
    image_url = page.get_by_role("link", name="Abrir comprovante", exact=True).get_attribute("href")
    assert context.request.get(base + image_url).headers["content-type"] == "image/png"
    anon = browser.new_context()
    assert anon.request.get(base + image_url).status == 401
    anon.close()
    page.get_by_role("button", name="Editar Microscópio E2E", exact=True).click()
    page.get_by_label("Produto", exact=True).fill("Microscópio revisado E2E")
    page.get_by_role("button", name="Conferir total", exact=True).click()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Confirmar compra", exact=True).click()
    page.get_by_role("heading", name="Microscópio revisado E2E", exact=True).wait_for()
    page.get_by_role("link", name="Espaço", exact=True).click()
    page.get_by_role("button", name="+ Nova gaveta", exact=True).click()
    page.get_by_label("Nome da gaveta", exact=True).fill("Ciência E2E")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Salvar gaveta", exact=True).click()
    page.get_by_text("▣ Ciência E2E · 0", exact=True).click()
    page.get_by_role("button", name="Adicionar link a Ciência E2E", exact=True).click()
    page.get_by_label("Título do link", exact=True).fill("Referência E2E")
    page.get_by_label("URL do link", exact=True).fill("https://example.org/biology")
    page.get_by_label("Etiquetas separadas por vírgula", exact=True).fill("células,estudo")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Salvar link", exact=True).click()
    page.get_by_role("link", name="Referência E2E", exact=True).wait_for()
    assert "noopener" in page.get_by_role("link", name="Referência E2E", exact=True).get_attribute(
        "rel"
    )
    page.get_by_role("button", name="Favoritar Referência E2E", exact=True).click()
    page.get_by_label("Somente favoritos", exact=True).check()
    page.get_by_label("Pesquisar links e etiquetas", exact=True).fill("células")
    page.get_by_role("link", name="Referência E2E", exact=True).wait_for()
    page.reload()
    page.get_by_text("▣ Ciência E2E · 1", exact=True).click()
    page.get_by_role("link", name="Referência E2E", exact=True).wait_for()
    for destination in ("Espaço", "Compras"):
        page.set_viewport_size({"width": 390, "height": 844})
        if destination == "Compras":
            page.get_by_role("button", name="Alternar menu", exact=True).click()
            page.get_by_role("link", name=destination, exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), destination
        page.screenshot(path="/tmp/saly-" + destination.lower() + ".png", full_page=True)
    page.evaluate("navigator.serviceWorker.ready.then(()=>true)")
    page.goto(base + "/offline")
    page.get_by_label("Senha do cofre", exact=True).fill("local-private-test-123")
    page.get_by_label("Autorizo copiar", exact=False).check()
    page.get_by_role("button", name="Criar cofre criptografado", exact=True).click()
    expect(page.get_by_role("button", name="Sincronizar agora", exact=True)).to_be_enabled()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("link", name="Compras e Espaço locais", exact=True).click()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Autorizar cópia de Compras e Espaço", exact=True).click()
    page.get_by_role("heading", name="Microscópio revisado E2E", exact=True).wait_for()
    context.set_offline(True)
    page.get_by_label("Área local", exact=True).select_option("drawers")
    page.get_by_role("button", name="+ Registro pessoal local", exact=True).click()
    page.get_by_label("Nome da gaveta", exact=True).fill("Gaveta offline E2E")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar rascunho pessoal", exact=True).click()
    page.get_by_role("heading", name="Gaveta offline E2E", exact=True).wait_for()
    page.get_by_label("Área local", exact=True).select_option("purchases")
    page.get_by_role("button", name="+ Registro pessoal local", exact=True).click()
    page.get_by_label("Produto", exact=True).fill("Compra offline E2E")
    page.get_by_label("Preço unitário em reais", exact=True).fill("11,11")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar rascunho pessoal", exact=True).click()
    page.get_by_role("heading", name="Compra offline E2E", exact=True).wait_for()
    page.reload()
    page.get_by_label("Senha do cofre", exact=True).fill("local-private-test-123")
    page.get_by_role("button", name="Desbloquear cofre", exact=True).click()
    page.get_by_role("link", name="Compras e Espaço locais", exact=True).click()
    page.get_by_role("heading", name="Compra offline E2E", exact=True).wait_for()
    context.set_offline(False)
    page.get_by_text(
        "Sincronização concluída. Confira os conflitos, se houver.", exact=True
    ).wait_for()
    rows = context.request.get(base + "/api/purchases").json()
    assert any(p["product"] == "Compra offline E2E" and p["total_cents"] == 1111 for p in rows)
    assert any(
        d["name"] == "Gaveta offline E2E" for d in context.request.get(base + "/api/drawers").json()
    )
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "purchase preview/integer budget",
                    "private image upload and preview",
                    "anonymous denied",
                    "edit/reload",
                    "drawer/link/favorite/tag search",
                    "mobile",
                ],
                "page_errors": errors,
            },
            ensure_ascii=False,
        )
    )
    context.close()
    browser.close()
