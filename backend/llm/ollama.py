"""Private, CPU-bounded Ollama adapter. No remote fallback or model downloads."""

import asyncio
import json
import time

import httpx

from .. import storage as store
from .provider import ProviderError

MODELS = ("granite4:3b", "ministral-3:3b", "phi4-mini", "gemma3:4b")
LOCK = asyncio.Lock()
BASE = "http://127.0.0.1:11434"


def client():
    return httpx.AsyncClient(
        base_url=BASE,
        timeout=httpx.Timeout(180, connect=2),
        follow_redirects=False,
        trust_env=False,
    )


def selection(conversation=None):
    value = (conversation or {}).get("llm_choice", store.setting("llm_default", "remote"))
    return value if value in (*MODELS, "remote") else "remote"


async def catalog():
    try:
        async with client() as c:
            r = await c.get("/api/tags", timeout=3)
            r.raise_for_status()
            tags = r.json()["models"]
            if not isinstance(tags, list) or not all(isinstance(item, dict) for item in tags):
                raise ValueError("Catálogo local incompatível")
        result = []
        for name in MODELS:
            item = next((m for m in tags if m.get("name") in (name, name + ":latest")), None)
            probe = store.setting("ollama_probe:" + name, {})
            verified = bool(item and probe.get("digest") == item.get("digest") and probe.get("ok"))
            result.append(
                {
                    "id": name,
                    "status": "ready"
                    if verified
                    else probe.get("status", "installed_unverified")
                    if item and probe.get("digest") == item.get("digest")
                    else "installed_unverified"
                    if item
                    else "not_installed",
                    "size": item.get("size") if item else None,
                    "digest": item.get("digest") if item else None,
                    "probe": probe if item and probe.get("digest") == item.get("digest") else None,
                }
            )
        return {"server": "ready", "models": result}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        status = (
            "server_offline" if isinstance(error, httpx.ConnectError) else "communication_error"
        )
        return {"server": status, "models": [{"id": n, "status": status} for n in MODELS]}


class Ollama:
    configured = True
    local = True
    last_probe = None

    def __init__(self, model):
        if model not in MODELS:
            raise ValueError("Modelo local não permitido")
        self.model = model
        self.supports_tools = False

    async def health(self):
        info = await catalog()
        item = next(m for m in info["models"] if m["id"] == self.model)
        return {
            "model": self.model,
            "provider": "ollama",
            "configured": True,
            "model_ready": item["status"] == "ready",
            "reason": item["status"],
            "detail": "Modelo local verificado"
            if item["status"] == "ready"
            else "Teste o modelo local em Configurações → Sistema.",
            "local": item,
        }

    async def capabilities(self):
        try:
            async with client() as c:
                r = await c.post("/api/show", json={"model": self.model}, timeout=5)
                if r.status_code != 200:
                    raise ProviderError(
                        503,
                        "Modelo não instalado no Ollama. Execute o instalador no seu Codespace.",
                    )
                caps = r.json().get("capabilities", [])
            # Advertising a capability is not a functional test.
            self.supports_tools = False
            return {"declared": caps, "tools_verified": False, "vision_verified": False}
        except (httpx.HTTPError, ValueError, TypeError) as e:
            raise ProviderError(
                503, "Servidor Ollama local indisponível ou resposta incompatível."
            ) from e

    async def stream(self, messages, tools=None, **kwargs):
        async with LOCK:  # One request/model loaded at a time, including probes.
            await self.capabilities()
            # No tool schema is sent until this particular model has been functionally verified.
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "keep_alive": 0,
                "options": {
                    "num_ctx": 8192,
                    "num_predict": min(kwargs.get("max_tokens") or 1400, 1400),
                    "num_thread": 4,
                },
            }
            try:
                async with client() as c, c.stream("POST", "/api/chat", json=payload) as r:
                    if r.status_code != 200:
                        detail = (await r.aread())[:4096].decode(errors="replace").lower()
                        if "memory" in detail or "out of memory" in detail:
                            raise ProviderError(
                                507, "Memória insuficiente para este modelo/contexto no servidor."
                            )
                        raise ProviderError(
                            503,
                            "Ollama recusou a geração; confira memória disponível e instalação do modelo.",
                        )
                    done = False
                    async for line in r.aiter_lines():
                        if len(line) > 1_000_000:
                            raise ProviderError(502, "Resposta local acima do limite.")
                        if not line:
                            continue
                        event = json.loads(line)
                        if event.get("error"):
                            raise ProviderError(
                                503,
                                "Falha de geração local. Confira memória e logs privados do Ollama.",
                            )
                        text = event.get("message", {}).get("content", "")
                        if text:
                            yield {"text": text}
                        if event.get("done"):
                            done = True
                            yield {"done": True}
                    if not done:
                        raise ProviderError(
                            502,
                            "Fluxo local interrompido; nenhuma resposta concluída foi simulada.",
                        )
            except (httpx.HTTPError, ValueError, TypeError) as e:
                raise ProviderError(503, "Falha de comunicação com o Ollama local.") from e
            finally:
                # Cancellation closes the HTTP stream, then explicitly requests release of weights.
                try:
                    async with client() as c:
                        await c.post(
                            "/api/generate", json={"model": self.model, "keep_alive": 0}, timeout=3
                        )
                except httpx.HTTPError:
                    pass


async def probe(model):
    adapter = Ollama(model)
    info = next(m for m in (await catalog())["models"] if m["id"] == model)
    if not info.get("digest"):
        raise ProviderError(
            503,
            "Servidor ausente ou modelo não instalado; nenhum download automático foi iniciado.",
        )
    started = time.monotonic()
    text = ""
    caps = await adapter.capabilities()
    try:
        async for event in adapter.stream(
            [
                {
                    "role": "user",
                    "content": "Responda em português: quanto é 2 + 2? Explique em uma frase.",
                }
            ],
            max_tokens=96,
        ):
            text += event.get("text", "")
    except ProviderError as error:
        store.set_setting(
            "ollama_probe:" + model,
            {
                "ok": False,
                "digest": info["digest"],
                "status": "resource_error" if error.status == 507 else "communication_error",
                "detail": error.detail,
            },
        )
        raise
    result = {
        "ok": bool(text.strip()),
        "digest": info["digest"],
        "seconds": round(time.monotonic() - started, 3),
        "response": text[:2000],
        "capabilities": caps,
        "scope": "Geração textual real; ferramentas e visão não verificadas.",
    }
    store.set_setting("ollama_probe:" + model, result)
    return result
