"""One remote OpenAI-compatible model. No local runtime or static fallback."""

import asyncio
import json
import os
import re
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
    def valid_endpoint(self):
        parsed = urlparse(self.base)
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )

    @property
    def configured(self):
        return bool(self.key and self.model and self.valid_endpoint)

    def client(self):
        return httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10), follow_redirects=False)

    async def available_models(self):
        """Read the live catalog independently of a stale or empty model setting."""
        if not self.key or not self.valid_endpoint:
            raise ProviderError(503, "Revise a chave e a URL HTTPS do provedor no servidor.")
        try:
            async with self.client() as client:
                response = await client.get(
                    self.base + "/models", headers={"Authorization": "Bearer " + self.key}
                )
            if response.status_code != 200:
                detail = {
                    401: "Chave recusada pelo provedor. Revise a credencial no servidor.",
                    403: "Acesso ao provedor bloqueado pela rede ou pelas permissões da conta.",
                    429: "Cota temporária do provedor atingida. Aguarde antes de testar novamente.",
                }.get(response.status_code, "Não foi possível validar o provedor remoto.")
                raise ProviderError(response.status_code, detail)
            catalog = response.json()
            if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
                raise TypeError("invalid catalog")
            # Only IDs are exposed, never arbitrary response text or control characters.
            return sorted(
                {
                    item["id"]
                    for item in catalog["data"]
                    if isinstance(item, dict)
                    and item.get("active") is not False
                    and isinstance(item.get("id"), str)
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,199}", item["id"])
                }
            )
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise ProviderError(
                503, "Não foi possível ler o catálogo de modelos do provedor. Tente novamente."
            ) from error

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
            ready = self.model in await self.available_models()
            return {
                "model_ready": ready,
                "model": self.model,
                "provider": "remote",
                "configured": True,
                "reason": "ready" if ready else "model_unavailable",
                "detail": ""
                if ready
                else "Modelo não anunciado pelo provedor. Execute bash scripts/connect-model.sh para escolher um modelo do catálogo atual.",
            }
        except ProviderError as error:
            return {
                "model_ready": False,
                "model": self.model,
                "provider": "remote",
                "configured": True,
                "reason": "provider_" + str(error.status),
                "detail": error.detail,
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
