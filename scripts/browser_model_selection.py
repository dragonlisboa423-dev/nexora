"""Actual UI/backend switching against a CONTROLLED Ollama protocol fixture, not model inference."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from browser_navigation import go
from browser_support import PASSWORD, ROOT, test_server
from playwright.sync_api import expect, sync_playwright

CALLS = []


class OllamaFixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, data, ndjson=False):
        raw = (json.dumps(data) + ("\n" if ndjson else "")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson" if ndjson else "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        assert self.path == "/api/tags"
        self.reply(
            {
                "models": [
                    {"name": name, "digest": "fixture-" + name, "size": 1}
                    for name in ("phi4-mini:latest", "granite4:3b")
                ]
            }
        )

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            self.reply({"capabilities": ["completion"]})
        elif self.path == "/api/generate":
            self.reply({"done": True})
        else:
            assert self.path == "/api/chat"
            CALLS.append(body)
            # Exercise disabled controls during a real outstanding HTTP generation request.
            time.sleep(1)
            self.reply(
                {
                    "message": {"content": "Resposta controlada de teste: " + body["model"]},
                    "done": True,
                },
                ndjson=True,
            )


@contextmanager
def protocol_fixture():
    # Fail if an existing server owns the port; never terminate or modify a real Ollama.
    server = ThreadingHTTPServer(("127.0.0.1", 11434), OllamaFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


with (
    tempfile.TemporaryDirectory(prefix="saly-chat-ready-") as directory,
    protocol_fixture(),
    test_server(
        port=8016,
        extra_environment={
            "SALY_DATA_DIR": directory,
            "SALY_DATABASE_URL": "sqlite:///" + directory + "/db.sqlite3",
        },
    ) as base,
    sync_playwright() as p,
):
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium",
        headless=True,
        args=["--no-sandbox", "--enable-unsafe-swiftshader"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    expect(page.get_by_text("Um espaço para suas ideias crescerem.", exact=True)).to_have_count(0)
    selector = page.get_by_label("Modelo da conversa", exact=True)
    expect(selector).to_be_visible()  # No collapsed details, on desktop or phone.
    expect(selector).to_be_enabled()
    expect(selector).to_have_value("granite4:3b")
    health = page.request.get(base + "/api/health").json()
    assert health["can_chat"] and not health["model_ready"]
    selector.select_option("phi4-mini")
    expect(selector).to_be_enabled()
    expect(selector).to_have_value("phi4-mini")
    expect(page.locator(".model-availability")).to_contain_text("Modelo instalado")
    # Installed-but-unverified must permit the first real chat request, without a probe.
    page.get_by_placeholder("Compartilhe uma ideia com Saly…").fill("Primeira pergunta de teste.")
    send = page.get_by_role("button", name="Enviar mensagem", exact=True)
    expect(send).to_be_enabled()
    send.click()
    expect(selector).to_be_disabled()
    expect(page.locator(".message.assistant .markdown")).to_have_text(
        "Resposta controlada de teste: phi4-mini"
    )
    expect(selector).to_be_enabled()
    cid = page.request.get(base + "/api/conversations").json()[0]["id"]
    go(page, "Configurações")
    page.get_by_role("link", name="Sistema", exact=True).click()
    selector = page.get_by_label("Modelo da conversa", exact=True)
    expect(selector).to_have_value("phi4-mini")
    # A refused save must be visible and must not pretend the new choice was stored.
    page.route(
        "**/api/local-models/selection",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body=json.dumps({"detail": "Falha controlada ao salvar"}),
        ),
    )
    selector.select_option("granite4:3b")
    expect(page.locator(".local-models [role=alert]")).to_contain_text("Falha controlada ao salvar")
    expect(selector).to_be_enabled()
    expect(selector).to_have_value("phi4-mini")
    page.unroute("**/api/local-models/selection")
    selector.select_option("granite4:3b")
    expect(selector).to_be_enabled()
    choice = page.request.get(base + "/api/local-models?conversation_id=" + cid).json()
    assert choice["selected"] == "granite4:3b" and choice["default"] == "phi4-mini", choice
    # The installer's CLI writes the same readiness consumed by the live application.
    report = Path(directory) / "probe.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/probe-ollama.py"),
            "granite4:3b",
            "--report",
            str(report),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "SALY_DATA_DIR": directory,
            "SALY_DATABASE_URL": "sqlite:///" + directory + "/db.sqlite3",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Testando geração local" in result.stdout
    assert json.loads(report.read_text())["models"][0]["status"] == "functional"
    assert page.request.get(base + "/api/health?conversation_id=" + cid).json()["model_ready"]
    page.locator(".model-options summary").click()
    page.get_by_role("button", name="Atualizar modelos", exact=True).click()
    expect(selector).to_be_enabled(timeout=15000)
    # Changing settings affects this same active conversation, not only a future one.
    page.get_by_role("navigation", name="Áreas principais", exact=True).get_by_role(
        "link", name="Conversa", exact=True
    ).click()
    expect(selector).to_have_value("granite4:3b")
    page.get_by_placeholder("Compartilhe uma ideia com Saly…").fill("Segunda pergunta de teste.")
    expect(send).to_be_enabled()
    send.click()
    expect(page.locator(".message.assistant .markdown").last).to_have_text(
        "Resposta controlada de teste: granite4:3b"
    )
    expect(selector).to_be_enabled()
    messages = page.request.get(base + "/api/conversations/" + cid).json()
    assert [m["model"] for m in messages if m["role"] == "assistant"] == [
        "phi4-mini",
        "granite4:3b",
    ]
    actual = [
        call for call in CALLS if call["messages"][-1]["content"] == "Segunda pergunta de teste."
    ][-1]
    assert any(turn["content"] == "Primeira pergunta de teste." for turn in actual["messages"])
    # Reload and reopen the saved history; per-conversation choice and both replies survive.
    page.reload()
    expect(selector).to_have_value("phi4-mini")
    page.get_by_role("button", name="Histórico de conversas", exact=True).click()
    page.get_by_role("button", name="Primeira pergunta de teste.", exact=True).click()
    expect(selector).to_have_value("granite4:3b")
    expect(page.locator(".message.assistant")).to_have_count(2)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(selector).to_be_visible()
    selector.select_option("phi4-mini")
    expect(selector).to_be_enabled()
    expect(selector).to_have_value("phi4-mini")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.screenshot(path="/tmp/saly-model-selection-mobile.png", full_page=True)
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "scope": "Controlled protocol, NOT real model inference",
                "flows": [
                    "visible selector; subtitle removed",
                    "first installed message works without a prior probe",
                    "installer CLI persists readiness to live app database",
                    "switch in Settings affects open conversation",
                    "actual routed IDs and retained history",
                    "reload/history restores choice",
                    "mobile switching; no JS errors",
                ],
            }
        )
    )
    browser.close()
