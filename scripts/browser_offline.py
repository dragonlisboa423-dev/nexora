"""Real encrypted IndexedDB/offline/conflict flows. Disposable server, no provider calls."""

import atexit
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory(prefix="saly-offline-e2e-")
PASSWORD = "disposable-offline-owner-123"
VAULT_PASSWORD = "disposable-vault-password-123"
BASE = "http://127.0.0.1:8002"
ENV = {
    **os.environ,
    "SALY_DATA_DIR": TEMP.name,
    "SALY_DATABASE_URL": "sqlite:///" + TEMP.name + "/saly-v2.sqlite3",
    "SALY_LLM_API_KEY": "",
    "GROQ_API_KEY": "",
    "SALY_OWNER_PASSWORD_HASH": "",
    "SALY_SECURE_COOKIE": "0",
    "SALY_EMBEDDING_URL": "",
    "SALY_GITHUB_TOKEN": "",
    "SALY_SEARCH_API_KEY": "",
}
subprocess.run(
    [
        sys.executable,
        "-c",
        "from backend import storage; from backend.security import set_owner; storage.initialize(); set_owner('"
        + PASSWORD
        + "')",
    ],
    cwd=ROOT,
    env=ENV,
    check=True,
)
SERVER = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8002"],
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
        urllib.request.urlopen(BASE + "/api/bootstrap", timeout=1)
        break
    except OSError:
        time.sleep(0.1)
else:
    raise RuntimeError("Servidor local não iniciou")

errors = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    memory = context.request.post(
        BASE + "/api/memories",
        data={"content": "PRIVATE_OFFLINE_MEMORY", "source": "consentimento de teste"},
    ).json()
    document = context.request.post(
        BASE + "/api/knowledge",
        multipart={
            "file": {
                "name": "offline.txt",
                "mimeType": "text/plain",
                "buffer": b"PRIVATE_OFFLINE_DOCUMENT",
            }
        },
        headers={"X-Saly-Request": "1"},
    ).json()
    for _ in range(100):
        if (
            context.request.get(BASE + "/api/knowledge/" + document["id"]).json()["status"]
            == "ready"
        ):
            break
        time.sleep(0.04)
    page.evaluate("navigator.serviceWorker.ready.then(()=>true)")
    page.goto(BASE + "/offline")
    page.get_by_role("heading", name="Cofre local da SALY", exact=True).wait_for()
    page.get_by_label("Senha do cofre", exact=True).fill(VAULT_PASSWORD)
    page.get_by_label("Autorizo copiar", exact=False).check()
    page.get_by_role("button", name="Criar cofre criptografado").click()
    page.get_by_text("PRIVATE_OFFLINE_MEMORY", exact=True).wait_for()
    expect(page.get_by_role("button", name="Sincronizar agora")).to_be_enabled()
    page.get_by_role("link", name="Documentos guardados", exact=True).click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Guardar documento neste cofre").click()
    page.get_by_text("Original e texto guardados", exact=False).wait_for()
    context.set_offline(True)
    with page.expect_download() as downloaded:
        page.get_by_role("button", name="Baixar original local").click()
    assert Path(downloaded.value.path()).read_bytes() == b"PRIVATE_OFFLINE_DOCUMENT"
    page.get_by_role("link", name="Memórias locais", exact=True).click()
    page.get_by_role("button", name="Editar localmente").click()
    page.get_by_label("Conteúdo da memória").fill("PRIVATE_OFFLINE_EDIT")
    page.get_by_role("button", name="Salvar rascunho local").click()
    page.get_by_text("PRIVATE_OFFLINE_EDIT", exact=True).wait_for()
    page.get_by_role("link", name="Cofre e sincronização", exact=True).click()
    with page.expect_download() as encrypted:
        page.get_by_role("button", name="Exportar backup criptografado").click()
    backup = json.loads(Path(encrypted.value.path()).read_text())
    assert backup["iterations"] == 210000 and "PRIVATE_OFFLINE" not in json.dumps(backup)
    assert VAULT_PASSWORD not in json.dumps(backup)
    page.reload()
    page.get_by_label("Senha do cofre", exact=True).fill("wrong-vault-password")
    page.get_by_role("button", name="Desbloquear cofre").click()
    page.get_by_role("alert").filter(has_text="incorreta ou backup danificado").wait_for()
    assert page.get_by_text("PRIVATE_OFFLINE_EDIT", exact=True).count() == 0
    page.get_by_label("Senha do cofre", exact=True).fill(VAULT_PASSWORD)
    page.get_by_role("button", name="Desbloquear cofre").click()
    page.get_by_text("PRIVATE_OFFLINE_EDIT", exact=True).wait_for()
    # A separate authenticated device changes the same record while this browser is offline.
    second = playwright.request.new_context(base_url=BASE)
    assert second.post("/api/auth/login", data={"password": PASSWORD}).status == 200
    assert (
        second.put("/api/memories/" + memory["id"], data={"content": "REMOTE_DEVICE_EDIT"}).status
        == 200
    )
    context.set_offline(False)
    page.get_by_role("heading", name="Revisar conflito", exact=True).wait_for()
    assert second.get("/api/memories").json()[0]["content"] == "REMOTE_DEVICE_EDIT"
    page.get_by_role("button", name="Manter versão do servidor").click()
    page.get_by_text("REMOTE_DEVICE_EDIT", exact=True).wait_for()
    context.set_offline(True)
    page.get_by_role("button", name="+ Memória local").click()
    page.get_by_label("Conteúdo da memória").fill("CREATED_WHILE_OFFLINE")
    page.get_by_role("button", name="Salvar rascunho local").click()
    page.get_by_text("CREATED_WHILE_OFFLINE", exact=True).wait_for()
    context.set_offline(False)
    for _ in range(100):
        records = second.get("/api/memories").json()
        if any(record["content"] == "CREATED_WHILE_OFFLINE" for record in records):
            break
        time.sleep(0.05)
    else:
        page.screenshot(path="/tmp/saly-offline-failure.png", full_page=True)
        raise AssertionError("Offline creation did not sync: " + str(page.get_by_role("alert").all_text_contents()))
    created = next(record for record in records if record["content"] == "CREATED_WHILE_OFFLINE")
    expect(page.get_by_role("button", name="Sincronizar agora")).to_be_enabled()
    page.get_by_role("button", name="Sincronizar agora").click()
    expect(page.get_by_role("button", name="Sincronizar agora")).to_be_enabled()
    assert (
        sum(
            record["content"] == "CREATED_WHILE_OFFLINE"
            for record in second.get("/api/memories").json()
        )
        == 1
    )
    context.set_offline(True)
    assert (
        second.post("/api/memories/delete", data={"ids": [created["id"]], "confirm": True}).status
        == 200
    )
    assert (
        second.delete(
            "/api/knowledge/" + document["id"] + "?confirm=true", headers={"X-Saly-Request": "1"}
        ).status
        == 200
    )
    context.set_offline(False)
    expect(page.get_by_text("CREATED_WHILE_OFFLINE", exact=True)).to_have_count(0)
    page.get_by_role("link", name="Documentos guardados", exact=True).click()
    expect(page.get_by_role("heading", name="offline.txt", exact=True)).to_have_count(0)
    # Restore is checked before replacement; a restored outbox stays paused until reviewed.
    page.get_by_role("button", name="Bloquear cofre").click()
    page.get_by_label("Selecionar backup criptografado", exact=False).set_input_files(
        {
            "name": "cofre.json",
            "mimeType": "application/json",
            "buffer": json.dumps(backup).encode(),
        }
    )
    page.get_by_label("Senha do cofre", exact=True).fill(VAULT_PASSWORD)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Validar e restaurar backup").click()
    page.get_by_role("status").filter(has_text="Backup validado e restaurado").wait_for()
    page.get_by_label("Senha do cofre", exact=True).fill(VAULT_PASSWORD)
    page.get_by_role("button", name="Desbloquear cofre").click()
    page.get_by_role("heading", name="Revisão após restauração", exact=True).wait_for()
    expect(page.get_by_role("button", name="Sincronizar agora")).to_be_disabled()
    assert second.get("/api/memories").json()[0]["content"] == "REMOTE_DEVICE_EDIT"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.screenshot(path="/tmp/saly-offline-private-mobile.png", full_page=True)
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "encrypted opt-in IndexedDB",
                    "selected document bytes offline",
                    "reload without network and wrong/correct unlock",
                    "two-device conflict",
                    "offline create and idempotent retry",
                    "remote deletion propagation",
                    "verified encrypted restore pauses sync",
                    "mobile layout",
                ],
                "provider_requests": 0,
                "page_errors": errors,
            }
        )
    )
    second.dispose()
    browser.close()
