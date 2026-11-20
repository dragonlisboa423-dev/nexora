"""Private, CPU-bounded Ollama adapter. No remote fallback or model downloads."""

import asyncio
import json
import os
import socket
import time

import httpx

from .. import storage as store
from .provider import ProviderError

PRIMARY = "qwen2.5:3b"
SECONDARY = "gemma3:4b"
RETIRED = "phi4-mini"
MODELS = (PRIMARY, SECONDARY, "granite4:3b", "ministral-3:3b")
WATER_QUESTION = "Explique quimicamente a molécula de água e suas propriedades."
KEEP_ALIVE_SECONDS = max(
    30, min(1800, int(os.environ.get("SALY_OLLAMA_KEEP_ALIVE_SECONDS", "300")))
)
LOCK = asyncio.Lock()
BASE = "http://127.0.0.1:11434"


def client():
    return httpx.AsyncClient(
        base_url=BASE,
        timeout=httpx.Timeout(300, connect=2),
        follow_redirects=False,
        trust_env=False,
    )


def configure_primary():
    """Apply the requested primary once, preserving prior preference as metadata."""
    with store.transaction():
        if not store.setting("qwen_primary_v1", {}).get("applied"):
            previous = store.setting("llm_default")
            store.set_setting("llm_default", PRIMARY)
            store.set_setting("qwen_primary_v1", {"applied": True, "previous_default": previous})


def selection(conversation=None):
    value = (conversation or {}).get("llm_choice") or store.setting("llm_default") or PRIMARY
    # Old conversation choices are remapped; historical message model labels stay intact.
    return value if value in (*MODELS, "remote") else PRIMARY


async def catalog(*, include_retired=False):
    model_ids = (*MODELS, RETIRED) if include_retired else MODELS
    try:
        async with client() as c:
            r = await c.get("/api/tags", timeout=3)
            r.raise_for_status()
            tags = r.json()["models"]
            if not isinstance(tags, list) or not all(isinstance(item, dict) for item in tags):
                raise ValueError("Catálogo local incompatível")
        result = []
        for name in model_ids:
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
        return {"server": status, "models": [{"id": n, "status": status} for n in model_ids]}


async def resolve_selection(conversation=None, *, remote_configured=False, inventory=None):
    # Defaults are choices, not availability claims. Never fall back from Qwen
    # to a different local/remote model if its weights/server are unavailable.
    return selection(conversation)


def record_failure(model, digest, error):
    if digest:
        store.set_setting(
            "ollama_probe:" + model,
            {
                "ok": False,
                "digest": digest,
                "status": "resource_error" if error.status == 507 else "communication_error",
                "detail": error.detail,
            },
        )


def generation_error(detail):
    if "memory" in str(detail)[:4096].lower():
        return ProviderError(507, "Memória insuficiente para este modelo/contexto no servidor.")
    return ProviderError(
        503, "Ollama recusou a geração; confira a instalação e os logs privados do servidor."
    )


class Ollama:
    configured = True
    local = True
    last_probe = None

    def __init__(self, model, *, diagnostic_only=False):
        if model not in MODELS and not (diagnostic_only and model == RETIRED):
            raise ValueError("Modelo local não permitido")
        self.model = model
        self.diagnostic_only = diagnostic_only
        self.supports_tools = False

    async def health(self):
        info = await catalog(include_retired=self.diagnostic_only)
        item = next(m for m in info["models"] if m["id"] == self.model)
        return {
            "model": self.model,
            "provider": "ollama",
            "configured": True,
            "model_ready": item["status"] == "ready",
            "can_chat": bool(item.get("digest")),
            "reason": item["status"],
            "detail": "Modelo local verificado"
            if item["status"] == "ready"
            else {
                "installed_unverified": "Modelo instalado. Envie uma mensagem para testar a geração, ou use Testar modelo local.",
                "server_offline": "Ollama desligado. Execute bash scripts/start-ollama.sh no servidor.",
                "not_installed": "Modelo ausente. Execute bash scripts/setup-ollama.sh no servidor.",
                "resource_error": "A última geração falhou por memória insuficiente. Libere RAM antes de tentar novamente.",
            }.get(
                item["status"],
                "Não foi possível confirmar a geração local. Confira o Ollama antes de tentar novamente.",
            ),
            "runtime": {
                "kind": "ollama-server-local",
                "endpoint": BASE,
                "hostname": socket.gethostname(),
                "codespace": os.environ.get("CODESPACE_NAME"),
                "keep_alive_seconds": KEEP_ALIVE_SECONDS,
            },
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
                data = r.json()
                if not isinstance(data, dict) or not isinstance(data.get("capabilities", []), list):
                    raise TypeError("Invalid local capabilities")
                caps = data.get("capabilities", [])
            # Advertising a capability is not a functional test.
            self.supports_tools = False
            return {"declared": caps, "tools_verified": False, "vision_verified": False}
        except (httpx.HTTPError, ValueError, TypeError) as e:
            raise ProviderError(
                503, "Servidor Ollama local indisponível ou resposta incompatível."
            ) from e

    async def stream(self, messages, tools=None, **kwargs):
        started = time.monotonic()
        async with LOCK:  # One request/model loaded at a time, including probes.
            info = next(
                m
                for m in (await catalog(include_retired=self.diagnostic_only))["models"]
                if m["id"] == self.model
            )
            digest = info.get("digest")
            # No tool schema is sent until this particular model has been functionally verified.
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "keep_alive": KEEP_ALIVE_SECONDS,
                "options": {
                    "num_ctx": 8192,
                    "num_predict": min(kwargs.get("max_tokens") or 1400, 1400),
                    "num_thread": 4,
                },
            }
            completed = False
            first_token_seconds = None
            metrics = {}
            try:
                if not digest:
                    raise ProviderError(
                        503, "Servidor Ollama indisponível ou modelo não instalado."
                    )
                caps = await self.capabilities()
                text_received = False
                async with client() as c, c.stream("POST", "/api/chat", json=payload) as r:
                    if r.status_code != 200:
                        raise generation_error((await r.aread())[:4096].decode(errors="replace"))
                    done = False
                    async for line in r.aiter_lines():
                        if len(line) > 1_000_000:
                            raise ProviderError(502, "Resposta local acima do limite.")
                        if not line:
                            continue
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            raise TypeError("Invalid local event")
                        if event.get("error"):
                            raise generation_error(event["error"])
                        message = event.get("message", {})
                        if not isinstance(message, dict) or not isinstance(
                            message.get("content", ""), str
                        ):
                            raise TypeError("Invalid local message")
                        text = message.get("content", "")
                        if text:
                            if first_token_seconds is None and text.strip():
                                first_token_seconds = round(time.monotonic() - started, 4)
                            text_received = text_received or bool(text.strip())
                            yield {"text": text}
                        if event.get("done") is True:
                            done = True
                            metrics = {
                                key: event[key]
                                for key in (
                                    "load_duration",
                                    "prompt_eval_count",
                                    "eval_count",
                                    "eval_duration",
                                    "done_reason",
                                )
                                if key in event
                            }
                            # Verification is recorded only after a complete, nonempty stream.
                            # A thinking-only or empty result cannot certify chat readiness.
                    if not done:
                        raise ProviderError(
                            502,
                            "Fluxo local interrompido; nenhuma resposta concluída foi simulada.",
                        )
                if not text_received:
                    raise ProviderError(
                        502, "O modelo não entregou texto. Nenhuma resposta foi simulada."
                    )
                current = next(
                    m
                    for m in (await catalog(include_retired=self.diagnostic_only))["models"]
                    if m["id"] == self.model
                )
                if current.get("digest") == digest:
                    self.last_probe = {
                        "ok": True,
                        "digest": digest,
                        "seconds": round(time.monotonic() - started, 3),
                        "first_token_seconds": first_token_seconds,
                        "runtime_metrics": metrics,
                        "keep_alive_seconds": KEEP_ALIVE_SECONDS,
                        "capabilities": caps,
                        "scope": "Geração textual concluída. Não verifica ferramentas, visão ou correção factual.",
                    }
                    # Never retain the user's message/answer in a readiness diagnostic.
                    store.set_setting("ollama_probe:" + self.model, self.last_probe)
                completed = True
                yield {"done": True}
            except ProviderError as error:
                record_failure(self.model, digest, error)
                raise
            except httpx.TimeoutException as cause:
                error = ProviderError(
                    504,
                    "O modelo local excedeu o tempo de espera ao carregar ou gerar texto. Confira a RAM e os logs do Ollama; tente uma mensagem curta.",
                )
                record_failure(self.model, digest, error)
                raise error from cause
            except (httpx.HTTPError, ValueError, TypeError) as e:
                error = ProviderError(503, "Falha de comunicação com o Ollama local.")
                record_failure(self.model, digest, error)
                raise error from e
            finally:
                # Completed responses keep one model warm for reuse. Failures and
                # cancellation release it; the server evicts on a different model.
                if not completed:
                    try:
                        async with client() as c:
                            await c.post(
                                "/api/generate",
                                json={"model": self.model, "keep_alive": 0},
                                timeout=3,
                            )
                    except httpx.HTTPError:
                        pass


async def probe(model, *, question=None, diagnostic_only=False):
    """The UI and installer share this actual generation + digest-bound record."""
    adapter = Ollama(model, diagnostic_only=diagnostic_only)
    text = ""
    characters = 0
    async for event in adapter.stream(
        [
            {
                "role": "user",
                "content": question
                or "Responda em português: quanto é 2 + 2? Explique em uma frase.",
            }
        ],
        max_tokens=512 if question else 96,
    ):
        characters += len(event.get("text", ""))
        text = (text + event.get("text", ""))[:16000]
    if not adapter.last_probe:
        raise ProviderError(
            409, "O modelo mudou durante o teste. Atualize a lista e tente novamente."
        )
    result = {
        **adapter.last_probe,
        "model": model,
        "response": text,
        "response_truncated": characters > len(text),
    }
    store.set_setting("ollama_probe:" + model, result)
    return result
