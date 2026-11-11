import asyncio

import httpx
import pytest

from backend.llm.provider import Provider, ProviderError


def test_remote_sse_and_429_retry(monkeypatch):
    p = Provider()
    p.key = "test-only-credential"
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            content=b'data: {"choices":[{"delta":{"content":"Ola"}}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
        )

    monkeypatch.setattr(
        p, "client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    async def run():
        return [event async for event in p.stream([{"role": "user", "content": "Hi"}])]

    events = asyncio.run(run())
    assert events == [{"text": "Ola"}, {"done": True}] and len(seen) == 2


def test_partial_stream_never_retried(monkeypatch):
    p = Provider()
    p.key = "test-only-credential"
    count = []

    def handler(request):
        count.append(1)
        return httpx.Response(
            200, content=b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        )

    monkeypatch.setattr(
        p, "client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    async def run():
        return [e async for e in p.stream([])]

    with pytest.raises(ProviderError):
        asyncio.run(run())
    assert len(count) == 1


def test_invalid_stream_and_missing_key(monkeypatch):
    p = Provider()
    p.key = ""

    async def run():
        return [e async for e in p.stream([])]

    with pytest.raises(ProviderError):
        asyncio.run(run())
    p.key = "test"
    monkeypatch.setattr(
        p,
        "client",
        lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=b"data: invalid\n\n")
            )
        ),
    )
    with pytest.raises(ProviderError):
        asyncio.run(run())


def test_ssrf_guards_block_internal_and_redirect_targets(monkeypatch):
    from backend.integrations import Integrations

    i = Integrations()
    i.web_hosts = {"localhost", "127.0.0.1", "allowed.example"}
    for url in (
        "http://allowed.example",
        "https://127.0.0.1",
        "https://localhost",
        "https://user:pass@allowed.example",
        "https://metadata.google.internal",
        "https://allowed.example:8443",
    ):
        with pytest.raises(ValueError):
            i.validate_url(url)
