"""Real Chromium flows with isolated data. No mocked production UI or user credentials."""

import atexit
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory(prefix="saly-e2e-")
ENV = {
    **os.environ,
    "SALY_DATA_DIR": TEMP.name,
    "SALY_DATABASE_URL": "sqlite:///" + TEMP.name + "/saly-v2.sqlite3",
    "SALY_LLM_API_KEY": "",
    "SALY_OWNER_PASSWORD_HASH": "",
    "SALY_EMBEDDING_URL": "",
    "SALY_GITHUB_TOKEN": "",
    "SALY_SEARCH_API_KEY": "",
}
subprocess.run(
    [
        sys.executable,
        "-c",
        "from backend import storage; from backend.security import set_owner; storage.initialize(); set_owner('disposable-test-owner-123')",
    ],
    cwd=ROOT,
    env=ENV,
    check=True,
)
SERVER = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8001"],
    cwd=ROOT,
    env=ENV,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)


@atexit.register
def cleanup():
    SERVER.terminate()
    SERVER.wait(timeout=10)
    TEMP.cleanup()


for _ in range(100):
    try:
        urllib.request.urlopen("http://127.0.0.1:8001/api/bootstrap", timeout=1)
        break
    except OSError:
        time.sleep(0.1)
else:
    raise RuntimeError("Servidor de teste não iniciou")
errors = []
with sync_playwright() as p:
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
    context = browser.new_context(viewport={"width": 1440, "height": 1100}, reduced_motion="reduce")
    context.grant_permissions(["microphone"], origin="http://127.0.0.1:8001")
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "console",
        lambda e: (
            errors.append(e.text)
            if e.type == "error" and ("THREE" in e.text or "shader" in e.text.lower())
            else None
        ),
    )
    page.add_init_script("""
    window.__micCalls=0;
    const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia=async(...args)=>{window.__micCalls++;const stream=await original(...args);window.__testStream=stream;return stream;};
    Object.defineProperty(window,'SpeechRecognition',{value:undefined});Object.defineProperty(window,'webkitSpeechRecognition',{value:undefined});
    """)
    page.goto("http://127.0.0.1:8001")
    assert page.get_by_label("Usuário", exact=True).count() == 0
    assert page.get_by_role("button", name="Criar meu espaço").count() == 0
    page.get_by_label("Senha privada", exact=True).fill("disposable-test-owner-123")
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    page.screenshot(path="/tmp/saly-smolin-desktop.png", full_page=True)
    # Controlled chat transport tests UI security/protocol only; no provider/encoder is contacted.
    external = []
    page.route(
        "https://untrusted.example/**",
        lambda route: (external.append(route.request.url), route.abort()),
    )
    page.route(
        "**/api/health",
        lambda route: route.fulfill(
            json={"model_ready": True, "model": "controlled-e2e-transport", "backend": "ready"}
        ),
    )
    text = "**Transporte controlado de teste.**\n\n<script>window.__xss=true</script>\n\n![externa](https://untrusted.example/private)"
    events = [
        {"type": "context", "conversation_id": "e2e-controlled", "sources": [], "memory_ids": []},
        {"type": "token", "text": text},
        {"type": "done", "content": text},
    ]
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(
            content_type="application/x-ndjson", body="".join(json.dumps(e) + "\n" for e in events)
        ),
    )
    page.reload()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.get_by_label("Mensagem para Saly").fill("Pergunta de teste do protocolo")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Enviar mensagem", exact=True).click()
    page.locator(".markdown strong").filter(has_text="Transporte controlado de teste.").wait_for()
    assert page.evaluate("window.__xss") is None
    assert not external and page.locator(".markdown img").count() == 0
    page.get_by_role("button", name="Regenerar", exact=True).click()
    page.wait_for_function("document.querySelectorAll('.markdown strong').length===2")
    page.unroute("**/api/chat")
    page.unroute("**/api/health")
    page.reload()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()

    assert page.evaluate("window.__micCalls") == 0
    page.get_by_role("button", name="Ativar microfone", exact=True).click()
    page.get_by_role("button", name="Parar microfone", exact=True).wait_for()
    assert page.evaluate("window.__testStream.getTracks().every(t=>t.readyState==='live')")
    page.get_by_role("button", name="Parar microfone", exact=True).click()
    assert page.evaluate("window.__testStream.getTracks().every(t=>t.readyState==='ended')")
    page.get_by_role("button", name="Fechar aviso").click()
    page.get_by_role("link", name="Memórias", exact=True).click()
    page.get_by_role("button", name="+ Nova memória").click()
    page.get_by_label("Conteúdo", exact=True).fill("Projeto molecular de referência")
    page.get_by_role("button", name="Salvar", exact=True).click()
    page.get_by_text("Projeto molecular de referência", exact=True).wait_for()
    page.reload()
    page.get_by_text("Projeto molecular de referência", exact=True).wait_for()
    page.get_by_role("link", name="Centro Smolin", exact=True).click()
    page.get_by_label("Importar documentos").set_input_files(
        {
            "name": "biologia.md",
            "mimeType": "text/markdown",
            "buffer": b"Biologia molecular e conhecimento de referencia",
        }
    )
    page.get_by_role("heading", name="biologia.md", exact=True).wait_for()
    page.get_by_label("Pesquisar Centro Smolin").fill("molecular")
    page.get_by_role("button", name="Pesquisar", exact=True).click()
    page.get_by_text("Biologia molecular e conhecimento de referencia", exact=True).wait_for()
    page.get_by_role("link", name="Agenda", exact=True).click()
    page.get_by_role("button", name="+ Novo lembrete").click()
    page.get_by_label("Título", exact=True).fill("Revisar biologia")
    page.get_by_label("Data e hora no fuso selecionado").fill("2026-11-12T14:00")
    page.get_by_role("button", name="Propor agendamento", exact=True).click()
    page.get_by_text("NÃO EXECUTADA", exact=True).wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Aprovar operação", exact=True).click()
    page.get_by_role("heading", name="Revisar biologia", exact=True).wait_for()
    page.get_by_role("link", name="Ferramentas e integrações", exact=True).click()
    page.get_by_role("button", name="Executar ou propor", exact=True).click()
    page.locator(".tool-result").filter(has_text="14").wait_for()
    page.goto("http://127.0.0.1:8001/evaluation")
    page.get_by_role("button", name="Executar avaliação", exact=True).click()
    page.get_by_text("8/8", exact=True).wait_for()
    for route, heading in [
        ("/voices", "Uma voz para Saly"),
        ("/settings/personality", "Personalidade"),
        ("/settings/privacy", "Privacidade"),
        ("/settings/system", "Sistema e desempenho"),
    ]:
        page.goto("http://127.0.0.1:8001" + route)
        page.get_by_role("heading", name=heading, exact=True).first.wait_for()
    # Explicitly exercise 2D fallback via a persisted setting, then mobile layout.
    page.get_by_label("Qualidade gráfica").select_option("2d")
    page.goto("http://127.0.0.1:8001")
    page.locator(".flat-core").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/saly-smolin-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.get_by_role("button", name="Alternar menu").click()
    page.get_by_role("link", name="Memórias", exact=True).click()
    page.get_by_role("heading", name="Memórias", exact=True).wait_for()
    page.evaluate("navigator.serviceWorker.ready.then(()=>true)")
    page.reload()
    caches = page.evaluate(
        "async () => { const all=[]; for(const name of await caches.keys()){const cache=await caches.open(name);for(const req of await cache.keys())all.push(req.url);}return all;}"
    )
    assert caches and all("/api/" not in url for url in caches)
    context.set_offline(True)
    page.goto("http://127.0.0.1:8001/offline-test")
    page.get_by_role("heading", name="Saly está sem conexão.").wait_for()
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "single-owner unlock/no registration",
                    "chat/Markdown/regeneration with controlled transport only; external images blocked",
                    "WebGL liquid core",
                    "explicit microphone capture/shutdown (test device)",
                    "global memory persistence",
                    "Smolin upload/search",
                    "reminder approval and execution",
                    "real calculator",
                    "evaluation",
                    "privacy/settings",
                    "2D fallback",
                    "mobile layout/navigation",
                    "public-only PWA cache",
                    "offline fallback",
                ],
                "page_errors": errors,
            },
            ensure_ascii=False,
        )
    )
    browser.close()
