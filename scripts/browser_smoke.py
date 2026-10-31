import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
temp = tempfile.TemporaryDirectory(prefix="saly-browser-")
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8001"],
    cwd=root,
    env={**os.environ, "SALY_DATA_DIR": temp.name},
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
import atexit


@atexit.register
def cleanup():
    process.terminate()
    process.wait(timeout=10)
    temp.cleanup()


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
        executable_path="/usr/bin/chromium",
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
    page.add_init_script("""
      window.__micCalls = 0;
      const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async (...args) => {
        window.__micCalls++;
        const stream = await original(...args);
        window.__testStream = stream;
        return stream;
      };
      Object.defineProperty(window, 'SpeechRecognition', {value: undefined});
      Object.defineProperty(window, 'webkitSpeechRecognition', {value: undefined});
    """)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8001")
    page.get_by_label("Usuário", exact=True).fill("browser-owner")
    page.get_by_label("Senha (mínimo 12 caracteres)").fill("browser-password-123")
    page.get_by_role(
        "button",
        name="Criar meu espaço"
        if page.get_by_role("button", name="Criar meu espaço").count()
        else "Entrar",
        exact=True,
    ).click()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.screenshot(path=str(Path(temp.name) / "desktop.png"), full_page=True)
    assert page.evaluate("window.__micCalls") == 0
    page.get_by_role("button", name="Ativar microfone", exact=True).click()
    page.get_by_role("button", name="Parar microfone", exact=True).wait_for()
    assert page.evaluate("window.__testStream.getTracks().every(t => t.readyState === 'live')")
    page.get_by_role("button", name="Parar microfone", exact=True).click()
    assert page.evaluate("window.__testStream.getTracks().every(t => t.readyState === 'ended')")
    page.get_by_role("button", name="Fechar aviso").click()
    page.get_by_role("link", name="Memórias", exact=True).click()
    page.get_by_role("button", name="+ Nova memória").click()
    page.get_by_label("Conteúdo", exact=True).fill("Meu projeto usa Python e SQLite")
    page.get_by_label("Tags (separadas por vírgula)").fill("teste,projeto")
    page.get_by_role("button", name="Salvar", exact=True).click()
    page.get_by_text("Meu projeto usa Python e SQLite", exact=True).first.wait_for()
    page.reload()
    page.get_by_text("Meu projeto usa Python e SQLite", exact=True).first.wait_for()
    page.get_by_role("link", name="Conhecimentos", exact=True).click()
    page.locator("input[type=file]").set_input_files(
        {
            "name": "nota.md",
            "mimeType": "text/markdown",
            "buffer": b"Fontes verificaveis sobre SQLite no projeto SALY.",
        }
    )
    page.get_by_role("heading", name="nota.md").first.wait_for()
    page.get_by_label("Pesquisar trechos").fill("SQLite")
    page.get_by_role("button", name="Pesquisar", exact=True).click()
    page.get_by_text(
        "Fontes verificaveis sobre SQLite no projeto SALY.", exact=True
    ).first.wait_for()
    page.get_by_role("link", name="Avaliação", exact=True).click()
    page.get_by_role("button", name="Executar avaliação", exact=True).click()
    page.get_by_text("8/8", exact=True).first.wait_for()
    for route, heading in [
        ("/voices", "Uma voz para Saly"),
        ("/activity", "Atividades e ferramentas"),
        ("/settings/personality", "Personalidade"),
        ("/settings/privacy", "Privacidade"),
        ("/settings/system", "Sistema e desempenho"),
    ]:
        page.goto("http://127.0.0.1:8001" + route)
        page.get_by_role("heading", name=heading, exact=True).first.wait_for()
    page.goto("http://127.0.0.1:8001")
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/saly-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Mobile overflow"
    )
    page.get_by_role("button", name="Alternar menu").click()
    page.get_by_role("link", name="Memórias", exact=True).click()
    page.get_by_role("heading", name="Memórias", exact=True).wait_for()
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "registration",
                    "desktop core",
                    "explicit microphone activation and track shutdown (Chromium test audio)",
                    "create memory",
                    "reload persistence",
                    "document import",
                    "FTS search",
                    "evaluation 8/8",
                    "settings routes",
                    "mobile navigation",
                    "no horizontal overflow",
                ],
                "page_errors": errors,
            },
            ensure_ascii=False,
        )
    )
    browser.close()
