"""Real interactions in the original draft; model calls are never sent."""

import json
import os

from browser_navigation import go
from browser_support import PASSWORD, test_server
from playwright.sync_api import expect, sync_playwright

with test_server(port=8007) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("button", name="Alternar menu", exact=True).click()
    go(page, "Biblioteca")
    page.get_by_role(
        "button", name="Ler Biologia — Volume I: Fundamentos da Vida", exact=True
    ).click()
    page.get_by_text("Opções do livro", exact=True).click()
    expect(page.get_by_role("button", name="Publicar versão revisada", exact=True)).to_be_disabled()
    page.get_by_label(
        "A reprodução sustenta linhagens, mas um indivíduo estéril pode estar vivo.", exact=True
    ).check()
    page.get_by_role("button", name="Conferir resposta", exact=True).click()
    page.get_by_text("Resposta correta.", exact=False).wait_for()
    page.get_by_label("Sumário do livro", exact=True).select_option("1")
    page.get_by_role("button", name="Executar cenário", exact=True).click()
    page.get_by_role("img", name="População calculada ao longo de 30 passos", exact=True).wait_for()
    page.get_by_role("button", name="Tabela de resultados", exact=True).count()
    page.get_by_label("Sumário do livro", exact=True).select_option("5")
    page.get_by_label("Fita codificante 5′ → 3′", exact=True).fill("ATGC")
    page.get_by_text("Complementar 3′ TACG 5′", exact=True).wait_for()
    page.get_by_text("RNA 5′ AUGC 3′", exact=True).wait_for()
    page.get_by_role("button", name="Aplicar substituição", exact=True).click()
    page.get_by_label("Sumário do livro", exact=True).select_option("6")
    page.get_by_label("Tipo celular", exact=True).select_option("prokaryote")
    expect(page.get_by_role("button", name="Núcleo", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Nucleoide", exact=True).click()
    page.get_by_text("sem envoltório nuclear", exact=False).wait_for()
    page.get_by_label("Tipo celular", exact=True).select_option("plant")
    page.get_by_role("button", name="Cloroplasto", exact=True).click()
    page.get_by_label("Sumário do livro", exact=True).select_option("8")
    page.get_by_label("Zoom digital", exact=True).fill("2")
    page.get_by_label("Foco didático", exact=True).fill("40")
    page.get_by_label("Iluminação digital (%)", exact=True).fill("120")
    page.get_by_text("não foi calibrada", exact=False).wait_for()
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.screenshot(path="/tmp/saly-biology-microscope.png", full_page=True)
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Perguntar sobre microscopia", exact=True).click()
    expect(page.get_by_role("textbox", name="Mensagem para Saly", exact=True)).to_have_value(
        __import__("re").compile("zoom digital 2")
    )
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "original draft never published",
                    "quiz attempt persisted",
                    "logistic chart computed",
                    "DNA complement/RNA",
                    "cell type distinctions",
                    "schematic microscope actual digital controls",
                    "authorized element context prepared",
                    "mobile",
                ],
                "page_errors": errors,
            }
        )
    )
    context.close()
    browser.close()
