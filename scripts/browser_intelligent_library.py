"""Real import/resume/reading/map and encrypted history; controlled ASR/chat test transport.
No claim of physical microphone ASR accuracy or real remote inference is made.
"""

import hashlib
import io
import json
import os
import shutil
import zipfile

from browser_support import PASSWORD, ROOT, test_server
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfWriter


def epub():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr(
            "META-INF/container.xml", '<container><rootfile full-path="OPS/book.opf"/></container>'
        )
        z.writestr(
            "OPS/book.opf",
            '<package><metadata><title>Livro de Genética</title><creator>Ana</creator></metadata><manifest><item id="first" href="z.xhtml" media-type="application/xhtml+xml"/><item id="second" href="a.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="first"/><itemref idref="second"/></spine></package>',
        )
        z.writestr(
            "OPS/z.xhtml",
            "<h1>Genética primeiro</h1><p>Genética mutação variabilidade evolução.</p><script>window.__bookExecuted=true</script>",
        )
        z.writestr(
            "OPS/a.xhtml", "<h1>Evolução depois</h1><p>Seleção natural explica adaptação.</p>"
        )
    return stream.getvalue()


environment = {}
if not shutil.which("espeak-ng"):
    runtime = ROOT / ".tools/espeak/runtime"
    if not (runtime / "usr/bin/espeak-ng").is_file():
        raise RuntimeError("eSpeak NG ausente: não é possível certificar resposta de voz real")
    environment = {
        "SALY_ESPEAK_BINARY": str(runtime / "usr/bin/espeak-ng"),
        "SALY_ESPEAK_DATA_PATH": str(runtime / "usr/lib/x86_64-linux-gnu/espeak-ng-data"),
        "SALY_ESPEAK_LIBRARY_PATH": str(runtime / "usr/lib/x86_64-linux-gnu"),
    }

with test_server(port=8011, extra_environment=environment) as base, sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=[
            "--no-sandbox",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
        ],
    )
    context = browser.new_context(viewport={"width": 1360, "height": 1000})
    context.add_init_script("""window.__recognizers=[]; window.__tracks=[];
      const gum=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia=async c=>{const stream=await gum(c);window.__tracks.push(...stream.getTracks());return stream;};
      window.SpeechRecognition=class {start(){window.__recognizers.push(this);} stop(){this.onend?.();} abort(){this.onend?.();}};
      window.__say=text=>{const r=window.__recognizers.at(-1);const result=[{transcript:text}];result.isFinal=true;r.onresult({resultIndex:0,results:[result]});};""")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("link", name="Centro Smolin", exact=True).click()
    page.get_by_label("Importar documentos", exact=True).set_input_files(
        [
            {"name": "genetica.epub", "mimeType": "application/epub+zip", "buffer": epub()},
            {
                "name": "evolucao.txt",
                "mimeType": "text/plain",
                "buffer": "Genética mutação variabilidade evolução adaptação.".encode(),
            },
            {
                "name": "astronomia.txt",
                "mimeType": "text/plain",
                "buffer": "Astronomia estrela galáxia telescópio.".encode(),
            },
        ]
    )
    for _ in range(300):
        docs = context.request.get(base + "/api/knowledge").json()
        if len(docs) == 3 and all(d["status"] == "ready" for d in docs):
            break
        page.wait_for_timeout(50)
    assert len(docs) == 3 and all(d["status"] == "ready" for d in docs)
    book = next(d for d in docs if d["kind"] == "epub")
    card = page.locator("article.card").filter(
        has=page.get_by_role("heading", name="genetica.epub", exact=True)
    )
    card.get_by_role("link", name="Ler texto por capítulos", exact=True).click()
    expect(page.get_by_role("heading", name="Genética primeiro", exact=True)).to_be_visible()
    page.get_by_role("button", name="Próximo capítulo", exact=True).click()
    expect(page.get_by_role("heading", name="Evolução depois", exact=True)).to_be_visible()
    for _ in range(100):
        if (
            context.request.get(base + f"/api/knowledge/{book['id']}/reading-position").json()[
                "page"
            ]
            == 2
        ):
            break
        page.wait_for_timeout(20)
    assert (
        context.request.get(base + f"/api/knowledge/{book['id']}/reading-position").json()["page"]
        == 2
    )
    page.reload()
    expect(page.get_by_role("heading", name="Evolução depois", exact=True)).to_be_visible()
    assert not page.evaluate("Boolean(window.__bookExecuted)")
    page.get_by_role("link", name="← Centro Smolin", exact=True).click()
    page.get_by_text("Mapa de conhecimento com fontes", exact=True).click()
    page.get_by_role("button", name="Conceito mutacao", exact=True).click()
    expect(page.get_by_role("region", name="Fontes do conceito")).to_contain_text("Genética")
    graph = context.request.get(base + "/api/knowledge/map").json()
    assert any(len({s["document_id"] for s in n["sources"]}) > 1 for n in graph["nodes"])
    page.get_by_label("Pesquisar em livro específico").select_option(book["id"])
    page.get_by_label("Pesquisar Centro Smolin").fill("genética")
    page.get_by_role("button", name="Pesquisar", exact=True).click()
    expect(page.get_by_text("Referência:", exact=False).first).to_be_visible()

    # A preserved transfer survives reload; a different file cannot resume its bytes.
    raw = b"\x00RAW_RESUME" * 500000
    transfer = context.request.post(
        base + "/api/knowledge/uploads", data={"name": "retomar.bin", "size": len(raw)}
    ).json()
    chunk = raw[: 2 * 1024 * 1024]
    assert context.request.put(
        base + f"/api/knowledge/uploads/{transfer['id']}?offset=0",
        data=chunk,
        headers={"Content-Type": "application/octet-stream", "X-Saly-Request": "1"},
    ).ok
    page.reload()
    resume = page.get_by_label("Retomar retomar.bin", exact=True)
    resume.set_input_files(
        {"name": "retomar.bin", "mimeType": "application/octet-stream", "buffer": b"X" * len(raw)}
    )
    page.get_by_text("O arquivo selecionado difere dos blocos", exact=False).wait_for()
    assert context.request.get(base + f"/api/knowledge/uploads/{transfer['id']}").json()[
        "offset"
    ] == len(chunk)
    resume.set_input_files(
        {"name": "retomar.bin", "mimeType": "application/octet-stream", "buffer": raw}
    )
    binary = page.locator("article.card").filter(
        has=page.get_by_role("heading", name="retomar.bin", exact=True)
    )
    binary.wait_for(timeout=30000)
    with page.expect_download() as downloading:
        binary.get_by_role("link", name="Baixar original", exact=True).click()
    from pathlib import Path

    assert (
        hashlib.sha256(Path(downloading.value.path()).read_bytes()).digest()
        == hashlib.sha256(raw).digest()
    )

    # Pause an actual parser, retain original, then resume via the actual interface.
    writer = PdfWriter()
    for _ in range(500):
        writer.add_blank_page(width=200, height=300)
    stream = io.BytesIO()
    writer.write(stream)
    result = context.request.post(
        base + "/api/knowledge",
        multipart={
            "file": {
                "name": "pausar.pdf",
                "mimeType": "application/pdf",
                "buffer": stream.getvalue(),
            }
        },
        headers={"X-Saly-Request": "1"},
    ).json()
    paused = context.request.post(base + f"/api/knowledge/jobs/{result['job_id']}/pause", data={})
    assert paused.ok, paused.text()
    page.reload()
    panel = (
        page.locator("div.card")
        .filter(has=page.get_by_text("pausar.pdf", exact=False))
        .filter(has=page.get_by_role("button", name="Retomar processamento", exact=True))
    )
    panel.get_by_role("button", name="Retomar processamento", exact=True).click()
    for _ in range(400):
        doc = context.request.get(base + f"/api/knowledge/{result['id']}").json()
        if doc["status"] not in ["queued", "processing", "paused"]:
            break
        page.wait_for_timeout(30)
    assert doc["status"] == "ocr_required"

    # Controlled ASR and LLM transport exercise the voice state machine, not real ASR/inference.
    settings = context.request.get(base + "/api/settings").json()
    settings["privacy"]["remoteConsent"] = True
    settings["voice"]["voiceURI"] = "saly-espeak:pt-br-f3"
    assert context.request.put(base + "/api/settings", data=settings).ok
    page.route(
        "**/api/health", lambda route: route.fulfill(json={"model_ready": True, "backend": "ready"})
    )
    commands = []

    def chat(route):
        commands.append(route.request.post_data_json["message"])
        events = [
            {"type": "context", "conversation_id": "controlled", "sources": [], "memory_ids": []},
            {"type": "token", "text": "Olá."},
            {"type": "done", "content": "Olá."},
        ]
        route.fulfill(
            content_type="application/x-ndjson", body="".join(json.dumps(e) + "\n" for e in events)
        )

    page.route("**/api/chat", chat)
    page.goto(base)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Modo de voz SALY", exact=True).click()
    page.wait_for_function("window.__recognizers.length>0")
    page.evaluate("window.__say('pergunta sem nome')")
    assert not commands
    page.evaluate("window.__say('SALY explique genética')")
    page.wait_for_function("document.body.innerText.includes('Olá.')")
    for _ in range(200):
        if page.evaluate("window.__recognizers.length") >= 2:
            break
        page.wait_for_timeout(50)
    assert page.evaluate("window.__recognizers.length") >= 2, page.locator("body").inner_text()
    page.evaluate("window.__say('e a evolução?')")
    for _ in range(100):
        if len(commands) == 2:
            break
        page.wait_for_timeout(40)
    assert commands == ["explique genética", "e a evolução?"]
    page.get_by_role("button", name="Desligar modo de voz", exact=True).click()
    assert page.evaluate('window.__tracks.every(t=>t.readyState==="ended")')

    # Controlled permission denial must disable the mode rather than retry in a loop.
    page.evaluate(
        "() => { navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('denied','NotAllowedError')); }"
    )
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Modo de voz SALY", exact=True).click()
    page.get_by_text(
        "Não foi possível acessar o microfone. Confira as permissões.", exact=True
    ).wait_for()
    expect(page.get_by_role("button", name="Modo de voz SALY", exact=True)).to_be_visible()
    assert page.evaluate('window.__tracks.every(t=>t.readyState==="ended")')

    # Explicit snapshot fixture; real encryption, IndexedDB, reload and offline UI.
    page.route(
        "**/api/conversations",
        lambda route: route.fulfill(
            json=[{"id": "history-fixture", "title": "Histórico escolhido"}]
        ),
    )
    page.route(
        "**/api/conversations/history-fixture/snapshot",
        lambda route: route.fulfill(
            json={
                "id": "history-fixture",
                "title": "Histórico escolhido",
                "copiedAt": "2026-11-17T00:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": "PRIVATE_HISTORY_SELECTED",
                        "created": "2026-11-17T00:00:00Z",
                    }
                ],
            }
        ),
    )
    page.goto(base + "/offline")
    page.get_by_label("Senha do cofre", exact=True).fill("private-offline-test-123")
    page.get_by_label("Autorizo copiar", exact=False).check()
    page.get_by_role("button", name="Criar cofre criptografado", exact=True).click()
    page.get_by_role("link", name="Histórico guardado", exact=True).click()
    page.get_by_role("button", name="Escolher conversa do servidor", exact=True).click()
    page.get_by_role("button", name="Guardar conversa no cofre", exact=True).click()
    page.get_by_text("Histórico escolhido · cópia de", exact=False).click()
    page.get_by_text("PRIVATE_HISTORY_SELECTED", exact=True).wait_for()
    page.evaluate("navigator.serviceWorker.ready.then(()=>true)")
    context.set_offline(True)
    page.reload()
    page.get_by_label("Senha do cofre", exact=True).fill("private-offline-test-123")
    page.get_by_role("button", name="Desbloquear cofre", exact=True).click()
    page.get_by_role("link", name="Histórico guardado", exact=True).click()
    page.get_by_text("Histórico escolhido · cópia de", exact=False).click()
    page.get_by_text("PRIVATE_HISTORY_SELECTED", exact=True).wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.screenshot(path="/tmp/saly-library-history-mobile.png", full_page=True)
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "files": "multiple EPUB/text, verified block resume, actual parser pause/resume",
                "knowledge": "spine reader, persistent position, cross-book graph sources, scoped search",
                "voice": "controlled ASR/chat/permission denial; actual PCM response; tracks stopped",
                "offline": "selected history fixture encrypted, reloaded and read without network; mobile no overflow",
                "page_errors": errors,
            }
        )
    )
    browser.close()
