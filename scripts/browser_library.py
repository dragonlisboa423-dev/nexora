"""Manual authoring and private reader with actual database writes."""

import json
import os

from browser_support import PASSWORD, test_server
from playwright.sync_api import expect, sync_playwright

with test_server(port=8006) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("link", name="Biblioteca", exact=True).click()
    page.get_by_role("button", name="+ Criar livro manual", exact=True).click()
    page.get_by_label("Título do livro", exact=True).fill("Livro manual E2E")
    page.get_by_role("button", name="Adicionar capítulo", exact=True).click()
    page.get_by_label("Título do capítulo", exact=True).fill("Capítulo E2E")
    page.get_by_role("button", name="Adicionar página", exact=True).click()
    page.get_by_label("Título da página", exact=True).fill("Página inicial E2E")
    page.get_by_label("Texto da página em Markdown", exact=True).fill(
        "## Uma pergunta investigável\nTexto original editado manualmente para este teste."
    )
    page.get_by_role("button", name="Adicionar página", exact=True).click()
    page.get_by_label("Título da página", exact=True).fill("Segunda página E2E")
    page.get_by_label("Texto da página em Markdown", exact=True).fill(
        "Conteúdo da segunda página, com referência a células."
    )
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Salvar versão manual", exact=True).click()
    page.get_by_text("Versão manual salva.", exact=False).wait_for()
    page.get_by_role("button", name="Pré-visualizar rascunho", exact=True).click()
    page.get_by_role("article", name="Página 1: Página inicial E2E", exact=True).wait_for()
    page.get_by_role("article", name="Página 2: Segunda página E2E", exact=True).wait_for()
    page.get_by_role("button", name="Concluir página 1", exact=True).click()
    page.get_by_text("1 de 2 páginas concluídas.", exact=True).wait_for()
    page.get_by_role("button", name="Marcar página 1", exact=True).click()
    page.get_by_role("button", name="Remover marcador 1", exact=True).wait_for()
    page.get_by_label("Minha anotação", exact=True).fill("Nota privada E2E")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar anotação", exact=True).click()
    page.get_by_text("Nota privada E2E", exact=True).wait_for()
    page.get_by_label("Leitura vertical acessível, sem animação", exact=True).check()
    page.get_by_label("Pesquisar no livro", exact=True).fill("células")
    page.get_by_role("button", name="Segunda página E2E", exact=True).click()
    book = context.request.get(base + "/api/books").json()[0]
    progress = context.request.get(base + "/api/books/" + book["id"] + "/progress").json()
    page.reload()
    page.get_by_role("button", name="Abrir rascunho de Livro manual E2E", exact=True).click()
    page.get_by_role("article", name="Página 2: Segunda página E2E", exact=True).wait_for()
    page.get_by_role("button", name="Editar rascunho manual", exact=True).click()
    page.get_by_label("Estado editorial", exact=True).select_option("review")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Salvar versão manual", exact=True).click()
    expect(page.get_by_role("button", name="Publicar versão revisada", exact=True)).to_be_enabled()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Publicar versão revisada", exact=True).click()
    page.get_by_text("Exibindo edição publicada", exact=False).wait_for()
    assert (
        context.request.get(base + "/api/books/" + book["id"] + "?edition_name=published").json()[
            "title"
        ]
        == "Livro manual E2E"
    )
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    assert page.get_by_role("article", name="Página 2: Segunda página E2E", exact=True).count() == 1
    page.screenshot(path="/tmp/saly-book-mobile.png", full_page=True)
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Perguntar à SALY sobre esta página", exact=True).click()
    expect(page.get_by_role("textbox", name="Mensagem para Saly")).to_contain_text(
        "Livro manual E2E"
    )
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "manual chapter/page authoring",
                    "real version save",
                    "double/single page reader",
                    "progress/bookmark/annotation",
                    "search/last page",
                    "explicit review/publication",
                    "context prepared without sending",
                    "mobile",
                ],
                "page_errors": errors,
            }
        )
    )
    context.close()
    browser.close()
