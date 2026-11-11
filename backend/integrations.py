"""Optional integrations. Credentials never enter model messages or frontend bundles."""

import asyncio
import base64
import ipaddress
import os
import socket
from urllib.parse import urlparse

import httpx


class Integrations:
    def __init__(self):
        self.repo = os.environ.get("SALY_GITHUB_REPOSITORY", "")
        self.token = os.environ.get("SALY_GITHUB_TOKEN", "")
        self.search_key = os.environ.get("SALY_SEARCH_API_KEY", "")
        self.web_hosts = {
            x.strip().lower()
            for x in os.environ.get("SALY_WEB_ALLOWED_DOMAINS", "").split(",")
            if x.strip()
        }

    @property
    def github_ready(self):
        return bool(self.token and len(self.repo.split("/")) == 2)

    async def github(self, method, path, body=None):
        if not self.github_ready:
            raise ValueError("Integração GitHub não configurada")
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
            r = await c.request(
                method,
                "https://api.github.com/repos/" + self.repo + path,
                headers={
                    "Authorization": "Bearer " + self.token,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json=body,
            )
            r.raise_for_status()
            return r.json()

    async def read_file(self, path):
        if (
            path.startswith("/")
            or ".." in path.split("/")
            or any(c in path for c in ("?", "#", "\\"))
        ):
            raise ValueError("Caminho inválido")
        from urllib.parse import quote

        result = await self.github("GET", "/contents/" + quote(path, safe="/"))
        if not isinstance(result, dict) or result.get("size", 0) > 500_000:
            raise ValueError("Arquivo indisponível ou grande demais")
        return {
            "path": path,
            "sha": result["sha"],
            "content": base64.b64decode(result["content"]).decode("utf-8"),
        }

    async def search_web(self, query):
        if not self.search_key:
            raise ValueError("Pesquisa web não configurada")
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as c:
            r = await c.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={"X-Subscription-Token": self.search_key},
            )
            r.raise_for_status()
        return [
            {"title": x["title"], "url": x["url"], "excerpt": x.get("description", "")}
            for x in r.json().get("web", {}).get("results", [])
        ][:5]

    def validate_url(self, url):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.hostname not in self.web_hosts
        ):
            raise ValueError("Destino não autorizado para leitura")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(item[4][0]).is_global for item in addresses
        ):
            raise ValueError("Endereço privado ou reservado bloqueado")
        return url

    async def read_web(self, url):
        await asyncio.to_thread(self.validate_url, url)
        async with (
            httpx.AsyncClient(timeout=15, follow_redirects=False) as c,
            c.stream("GET", url, headers={"Accept": "text/html,text/plain"}) as r,
        ):
            if r.is_redirect:
                raise ValueError("Redirecionamento não permitido")
            r.raise_for_status()
            if not any(t in r.headers.get("content-type", "") for t in ("text/html", "text/plain")):
                raise ValueError("Tipo de fonte não suportado")
            content = b""
            async for part in r.aiter_bytes():
                content += part
                if len(content) > 500_000:
                    raise ValueError("Fonte grande demais")
        # HTML is returned as data only; no scripts or remote assets are executed.
        from html.parser import HTMLParser

        class Reader(HTMLParser):
            def __init__(self):
                super().__init__()
                self.skip = 0
                self.parts = []

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style"):
                    self.skip += 1

            def handle_endtag(self, tag):
                if tag in ("script", "style"):
                    self.skip = max(0, self.skip - 1)

            def handle_data(self, data):
                if not self.skip:
                    self.parts.append(data)

        parser = Reader()
        parser.feed(content.decode("utf-8", errors="replace"))
        return {
            "url": url,
            "content": " ".join(parser.parts)[:12000],
            "trust": "untrusted_web_source",
        }


integrations = Integrations()
