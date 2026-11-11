"""One remote OpenAI-compatible model. No local runtime or static fallback."""

import asyncio
import json
import os
from urllib.parse import urlparse

import httpx


class ProviderError(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail
        super().__init__(detail)


class Provider:
    def __init__(self):
        self.base = os.environ.get("SALY_LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip(
            "/"
        )
        self.model = os.environ.get("SALY_MODEL", "llama-3.3-70b-versatile")
        self.key = os.environ.get("SALY_LLM_API_KEY") or (
            os.environ.get("GROQ_API_KEY", "")
            if urlparse(self.base).hostname == "api.groq.com"
            else ""
        )
        self.last_probe = None
        self.attempts = 3

    @property
    def configured(self):
        parsed = urlparse(self.base)
        return bool(
            self.key
            and self.model
            and parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )

    def client(self):
        return httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10), follow_redirects=False)

    async def health(self):
        if not self.configured:
            return {
                "model_ready": False,
                "model": self.model,
                "detail": "Execute bash scripts/connect-model.sh no servidor para conectar o modelo e o agente. A chave é solicitada no terminal privado."
                if not self.key
                else "Revise a configuração: modelo não vazio e URL HTTPS sem credenciais ou parâmetros na URL.",
                "provider": "remote",
                "configured": False,
                "reason": "missing_key" if not self.key else "invalid_configuration",
            }
        try:
            async with self.client() as c:
                r = await c.get(
                    self.base + "/models", headers={"Authorization": "Bearer " + self.key}
                )
                if r.status_code != 200:
                    detail = {
                        401: "Chave recusada pelo provedor. Revise a credencial no servidor.",
                        403: "Acesso ao provedor bloqueado pela rede ou pelas permissões da conta.",
                        429: "Cota temporária do provedor atingida. Aguarde antes de testar novamente.",
                    }.get(r.status_code, "Não foi possível validar o provedor remoto")
                    return {
                        "model_ready": False,
                        "model": self.model,
                        "provider": "remote",
                        "configured": True,
                        "reason": "provider_" + str(r.status_code),
                        "detail": detail,
                    }
                ready = any(m["id"] == self.model for m in r.json().get("data", []))
            return {
                "model_ready": ready,
                "model": self.model,
                "provider": "remote",
                "configured": True,
                "reason": "ready" if ready else "model_unavailable",
                "detail": "" if ready else "Modelo não anunciado pelo provedor; revise SALY_MODEL.",
            }
        except (httpx.HTTPError, ValueError, ProviderError):
            return {
                "model_ready": False,
                "model": self.model,
                "provider": "remote",
                "configured": True,
                "detail": "Provedor inacessível, credencial recusada ou limite de uso. Verifique a configuração.",
            }

    async def stream(self, messages, tools=None, *, tool_choice="auto", max_tokens=None):
        if not self.configured:
            raise ProviderError(503, "Provedor remoto não configurado")
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens
            if max_tokens is not None
            else int(os.environ.get("SALY_MAX_OUTPUT_TOKENS", "1400")),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        # Retry only before receiving any generation. Do not repeat a partial stream.
        for attempt in range(self.attempts):
            try:
                async with (
                    self.client() as c,
                    c.stream(
                        "POST",
                        self.base + "/chat/completions",
                        headers={
                            "Authorization": "Bearer " + self.key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    ) as r,
                ):
                    if r.status_code in (429, 502, 503) and attempt + 1 < self.attempts:
                        try:
                            delay = min(10, max(0, float(r.headers.get("retry-after", 2**attempt))))
                        except ValueError:
                            delay = 2**attempt
                        await asyncio.sleep(delay)
                        continue
                    if r.status_code != 200:
                        raise ProviderError(
                            r.status_code,
                            "Limite do provedor atingido"
                            if r.status_code == 429
                            else "Solicitação recusada pelo provedor remoto",
                        )
                    async for line in r.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            yield {"done": True}
                            return
                        try:
                            event = json.loads(data)
                        except ValueError:
                            raise ProviderError(502, "Fluxo inválido do provedor") from None
                        choices = event.get("choices", [])
                        if not choices:
                            continue
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            yield {"text": delta["content"]}
                        if delta.get("tool_calls"):
                            yield {"tool_calls": delta["tool_calls"]}
                        if choice.get("finish_reason") in ("stop", "tool_calls"):
                            yield {"done": True}
                            return
                    raise ProviderError(
                        502, "O provedor encerrou o fluxo antes de confirmar a resposta"
                    )
            except httpx.HTTPError:
                raise ProviderError(502, "Falha de conexão com o provedor remoto") from None
        raise ProviderError(429, "Limite temporário do provedor")
