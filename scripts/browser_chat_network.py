"""Actual browser through an idle-cutoff proxy, with a CONTROLLED local model protocol."""

import http.client
import json
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from browser_support import PASSWORD, test_server
from playwright.sync_api import expect, sync_playwright

STATE = {"heartbeats": 0, "requests": 0, "drop": False}


class Model(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, body):
        raw = json.dumps(body).encode() + b"\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected when the disconnected chat cancels its provider request.

    def do_GET(self):
        self.reply({"models": [{"name": "qwen2.5:3b", "digest": "controlled", "size": 1}]})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/api/show":
            self.reply({"capabilities": ["completion"]})
        elif self.path == "/api/generate":
            self.reply({"done": True})
        else:
            time.sleep(1.2)  # Longer than the proxy's .35s idle deadline.
            self.reply({"message": {"content": "Resposta controlada após espera."}, "done": True})


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def forward(self):
        chat = self.path == "/api/chat" and self.command == "POST"
        connection = http.client.HTTPConnection("127.0.0.1", 8018, timeout=0.35 if chat else 10)
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            connection.request(
                self.command,
                self.path,
                body=body,
                headers={
                    key: value
                    for key, value in self.headers.items()
                    if key.lower() not in {"connection", "transfer-encoding"}
                },
            )
            upstream = connection.getresponse()
            self.send_response(upstream.status)
            for key, value in upstream.getheaders():
                if key.lower() not in {
                    "connection",
                    "transfer-encoding",
                    "content-length",
                    "server",
                    "date",
                }:
                    self.send_header(key, value)
            if not chat:
                data = upstream.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            STATE["requests"] += 1
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                block = upstream.read1(65536)
                if not block:
                    break
                STATE["heartbeats"] += block.count(b'"type": "heartbeat"')
                self.wfile.write(f"{len(block):x}\r\n".encode() + block + b"\r\n")
                self.wfile.flush()
                if STATE["drop"]:
                    STATE["drop"] = False
                    self.close_connection = True
                    return  # Deliberate incomplete stream: browser must show an honest network error.
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (OSError, http.client.HTTPException):
            self.close_connection = True
        finally:
            connection.close()

    do_GET = forward
    do_POST = forward
    do_PUT = forward
    do_DELETE = forward


@contextmanager
def serve(port, handler):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


with (
    serve(11434, Model),
    test_server(port=8018, extra_environment={"SALY_CHAT_HEARTBEAT_SECONDS": ".1"}),
    serve(8019, Proxy),
    sync_playwright() as p,
):
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium",
        headless=True,
        args=["--no-sandbox", "--enable-unsafe-swiftshader"],
    )
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8019")
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    selector = page.get_by_label("Modelo da conversa", exact=True)
    expect(selector).to_have_value("qwen2.5:3b")
    textarea = page.get_by_placeholder("Compartilhe uma ideia com Saly…")
    textarea.fill("Pergunta de teste com carga lenta.")
    send = page.get_by_role("button", name="Enviar mensagem", exact=True)
    expect(send).to_be_enabled()
    send.click()
    expect(page.locator(".message.assistant .markdown")).to_have_text(
        "Resposta controlada após espera.", timeout=15000
    )
    assert STATE["heartbeats"] >= 2, STATE
    expect(selector).to_be_enabled()
    cid = page.request.get("http://127.0.0.1:8019/api/conversations").json()[0]["id"]
    STATE["drop"] = True
    textarea.fill("Teste de desconexão sem reenvio automático.")
    send.click()
    expect(page.locator("main [role=alert]")).to_contain_text(
        "A conexão com a SALY foi interrompida", timeout=15000
    )
    expect(selector).to_be_enabled()
    page.wait_for_timeout(1800)
    assert STATE["requests"] == 2, STATE  # No automatic replay after an uncertain response.
    messages = page.request.get("http://127.0.0.1:8019/api/conversations/" + cid).json()
    assert sum(message["role"] == "assistant" for message in messages) == 1, messages
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "scope": "CONTROLLED protocol, not real model inference",
                "heartbeats": STATE["heartbeats"],
                "flows": [
                    "delayed response survives proxy idle cutoff",
                    "honest browser disconnect message",
                    "no automatic retry or fake completed reply",
                    "producer cancelled on disconnected browser",
                ],
            }
        )
    )
    browser.close()
