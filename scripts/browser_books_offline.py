"""Selective encrypted book/media copy, real offline work and revision conflict."""

import io
import json
import os

from browser_support import PASSWORD, test_server
from PIL import Image
from playwright.sync_api import expect, sync_playwright

with test_server(port=8009) as base, sync_playwright() as playwright:
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
    page.get_by_role("heading", name="Olá. Eu sou Saly.", exact=True).wait_for()
    book = context.request.get(base + "/api/books").json()[0]
    key = book["id"]
    stream = io.BytesIO()
    Image.new("RGB", (70, 40), "green").save(stream, format="PNG")
    asset = context.request.post(
        base + "/api/books/" + key + "/image",
        multipart={
            "file": {"name": "book.png", "mimeType": "image/png", "buffer": stream.getvalue()}
        },
        headers={"X-Saly-Request": "1"},
    ).json()
    current = context.request.get(base + "/api/books/" + key).json()
    fields = [
        "title",
        "subtitle",
        "subject",
        "description",
        "language",
        "author",
        "license",
        "cover_asset_id",
        "cover_color",
        "publication_status",
        "chapters",
    ]
    data = {field: current[field] for field in fields}
    data["chapters"][0]["pages"][0]["blocks"].append(
        {
            "type": "image",
            "asset_id": asset["id"],
            "alt": "Imagem guardada offline E2E",
            "credit": "Esquema original do teste",
        }
    )
    assert context.request.patch(
        base + "/api/books/" + key,
        data={"data": data, "base_revision": current["revision"], "confirm": True},
    ).ok
    event = context.request.post(
        base + "/api/calendar/events",
        data={
            "data": {
                "title": "Evento para consulta offline E2E",
                "start_at": "2027-01-10T09:00",
                "end_at": "2027-01-10T10:00",
                "timezone": "America/Sao_Paulo",
                "alarm_minutes_before": 15,
            },
            "confirm": True,
        },
    )
    assert event.ok
    page.evaluate("navigator.serviceWorker.ready.then(()=>true)")
    page.goto(base + "/offline")
    page.get_by_label("Senha do cofre", exact=True).fill("private-offline-books-123")
    page.get_by_label("Autorizo copiar", exact=False).check()
    page.get_by_role("button", name="Criar cofre criptografado", exact=True).click()
    expect(page.get_by_role("button", name="Sincronizar agora", exact=True)).to_be_enabled()
    page.get_by_role("link", name="Agenda e alarmes guardados", exact=True).click()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar agenda e alarmes para consulta", exact=True).click()
    page.get_by_role(
        "heading", name="Evento para consulta offline E2E", exact=True
    ).first.wait_for()
    page.get_by_role("link", name="Livros guardados", exact=True).click()
    page.get_by_role("button", name="Consultar livros para baixar", exact=True).click()
    page.get_by_label("Incluir mídias privadas até 5 MB cada", exact=True).check()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar livro " + book["title"], exact=True).click()
    expect(page.get_by_alt_text("Imagem guardada offline E2E", exact=True)).to_be_visible()
    assert (
        page.get_by_alt_text("Imagem guardada offline E2E", exact=True)
        .get_attribute("src")
        .startswith("blob:")
    )
    context.set_offline(True)
    page.reload()
    page.get_by_label("Senha do cofre", exact=True).fill("private-offline-books-123")
    page.get_by_role("button", name="Desbloquear cofre", exact=True).click()
    page.get_by_role("link", name="Livros guardados", exact=True).click()
    page.get_by_role("link", name="Agenda e alarmes guardados", exact=True).click()
    page.get_by_role(
        "heading", name="Evento para consulta offline E2E", exact=True
    ).first.wait_for()
    page.get_by_role("link", name="Livros guardados", exact=True).click()
    page.get_by_label("Livro local", exact=True).select_option(key)
    expect(page.get_by_alt_text("Imagem guardada offline E2E", exact=True)).to_be_visible()
    page.get_by_role("button", name="Concluir página local", exact=True).click()
    page.get_by_text("1 página(s) concluída(s).", exact=True).wait_for()
    page.get_by_label("Anotação local do livro", exact=True).fill(
        "Nota do livro criada sem rede E2E"
    )
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Guardar anotação local", exact=True).click()
    page.get_by_text("Nota do livro criada sem rede E2E", exact=True).wait_for()
    other = browser.new_context()
    assert other.request.post(base + "/api/auth/login", data={"password": PASSWORD}).ok
    remote = other.request.put(
        base + "/api/books/" + key + "/progress",
        data={
            "current_page_id": "bio-p2",
            "completed_pages": ["bio-p2"],
            "bookmarks": [],
            "quiz_attempts": {},
            "base_revision": 0,
        },
    )
    assert remote.ok
    context.set_offline(False)
    page.get_by_role("heading", name="Revisar sincronização do livro", exact=True).wait_for()
    assert other.request.get(base + "/api/books/" + key + "/progress").json()[
        "completed_pages"
    ] == ["bio-p2"]
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Reenviar progresso local revisado", exact=True).click()
    page.wait_for_function(
        """async(key)=>{const p=await(await fetch('/api/books/'+key+'/progress')).json();const n=await(await fetch('/api/books/'+key+'/annotations')).json();return p.completed_pages.includes('bio-p1')&&n.length===1;}""",
        arg=key,
    )
    page.get_by_role("button", name="Sincronizar agora", exact=True).click()
    expect(page.get_by_role("button", name="Sincronizar agora", exact=True)).to_be_enabled()
    assert len(other.request.get(base + "/api/books/" + key + "/annotations").json()) == 1
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.wait_for_function(
        "document.querySelector('.sidebar').getBoundingClientRect().right <= 0.5"
    )
    page.screenshot(path="/tmp/saly-book-offline-mobile.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    latest = other.request.get(base + "/api/books/" + key).json()
    assert other.request.delete(
        base + "/api/books/" + key + "?confirm=true&base_revision=" + str(latest["revision"]),
        headers={"X-Saly-Request": "1"},
    ).ok
    page.get_by_role("button", name="Sincronizar agora", exact=True).click()
    page.get_by_text("Nenhum livro guardado neste dispositivo.", exact=True).wait_for()
    page.goto(base + "/laboratory")
    page.get_by_role("button", name="Testar recursos locais · sem API externa", exact=True).click()
    page.get_by_text("8 casos", exact=False).wait_for()
    reports = other.request.get(base + "/api/laboratory").json()
    assert reports[0]["kind"] == "feature-lab-v1" and reports[0]["provider_requests"] == 0
    page.get_by_role("button", name="Testar este dispositivo · som curto", exact=True).click()
    page.get_by_text("Resultados relatados pelo navegador", exact=False).wait_for()
    reports = other.request.get(base + "/api/laboratory").json()
    device = next(r for r in reports if r["kind"] == "device-lab-v1")
    cases = {c["id"]: c for c in device["results"]}
    assert cases["indexeddb"]["status"] == "passed" and cases["cache"]["status"] == "passed"
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "encrypted selective book/image download/checksum",
                    "offline reload/decrypt/blob image",
                    "offline completion and annotation",
                    "explicit two-device conflict",
                    "idempotent annotation sync",
                    "remote deletion propagation",
                    "local engines laboratory",
                    "real browser IndexedDB/PCM/cache probes",
                    "mobile",
                ],
                "provider_requests": 0,
                "page_errors": errors,
            }
        )
    )
    other.close()
    context.close()
    browser.close()
