"""Generation contracts. No paid provider or automatic billing activation."""

import base64
import os
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx

from . import storage as store


class ImageGenerationProvider(ABC):
    @abstractmethod
    def capabilities(self): ...

    @abstractmethod
    async def generate(self, prompt, steps): ...


class VideoGenerationProvider(ABC):
    @abstractmethod
    def capabilities(self): ...

    @abstractmethod
    async def generate(self, prompt): ...


class NoVideoProvider(VideoGenerationProvider):
    def capabilities(self):
        return {
            "status": "nao_configurada",
            "text_to_video": False,
            "image_to_video": False,
            "reason": "Sem modelo, GPU ou provedor gratuito conectado e testado.",
        }

    async def generate(self, prompt):
        raise ValueError("Geração de vídeo por IA não configurada")


class CloudflareImageProvider(ImageGenerationProvider):
    model = "@cf/black-forest-labs/flux-1-schnell"

    def capabilities(self):
        configured = bool(
            re.fullmatch(r"[a-fA-F0-9]{32}", os.environ.get("SALY_CF_ACCOUNT_ID", ""))
            and os.environ.get("SALY_CF_API_TOKEN")
        )
        reviewed = (
            os.environ.get("SALY_CF_WORKERS_FREE_CONFIRMED") == "1"
            and os.environ.get("SALY_CF_TERMS_REVIEWED") == "1"
        )
        enabled = configured and reviewed
        return {
            "provider": "Cloudflare Workers AI",
            "model": self.model,
            "status": "configurado_nao_testado" if enabled else "nao_configurada",
            "configured": enabled,
            "credentials_present": configured,
            "free_plan_and_terms_declared": reviewed,
            "text_to_image": enabled,
            "editing": False,
            "remote_cancellation": False,
            "daily_request_limit": 1,
            "reason": "Exige conta Workers Free sem cobrança, token no servidor, revisão dos termos BFL e confirmação explícita; teste real ainda necessário. A cota de Neurons é compartilhada com outros usos da conta.",
        }

    async def generate(self, prompt, steps=4):
        if not self.capabilities()["configured"]:
            raise ValueError("Cloudflare não configurada com plano gratuito e termos revisados")
        day = datetime.now(UTC).date().isoformat()
        with store.transaction():
            usage = store.setting("cf_image_daily_usage", {})
            if usage.get("day") == day and usage.get("requests", 0) >= 1:
                raise ValueError("Limite local conservador de uma requisição por dia UTC atingido")
            store.set_setting("cf_image_daily_usage", {"day": day, "requests": 1})
        # Fixed official origin/model. No redirects, alternate gateway or paid fallback.
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + os.environ["SALY_CF_ACCOUNT_ID"]
            + "/ai/run/"
            + self.model
        )
        async with (
            httpx.AsyncClient(
                timeout=httpx.Timeout(120, connect=10), follow_redirects=False
            ) as client,
            client.stream(
                "POST",
                url,
                headers={"Authorization": "Bearer " + os.environ["SALY_CF_API_TOKEN"]},
                json={"prompt": prompt, "steps": steps},
            ) as response,
        ):
            if response.status_code != 200:
                raise ValueError(
                    {
                        401: "Token recusado; reveja a configuração privada",
                        403: "Conta/rede sem permissão para o modelo",
                        429: "Cota atingida; não haverá cobrança alternativa nem nova tentativa automática",
                    }.get(response.status_code, "Provedor não concluiu a geração")
                )
            raw = bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > 12 * 1024 * 1024:
                    raise ValueError("Resposta do provedor acima do limite")
        import json

        try:
            body = json.loads(raw)
            if body.get("success") is False:
                raise ValueError()
            content = base64.b64decode(body["result"]["image"], validate=True)
            if not content:
                raise ValueError()
            return content
        except (ValueError, KeyError, TypeError):
            raise ValueError("Provedor retornou imagem inválida") from None


image_provider = CloudflareImageProvider()
video_provider = NoVideoProvider()
