"""Transport liveness during actual asynchronous gaps; no generated/fake answer tokens."""

import asyncio
import json

import anyio

from backend import streaming


def test_heartbeats_keep_connection_active_without_restarting_provider(monkeypatch):
    monkeypatch.setattr(streaming, "HEARTBEAT_SECONDS", 0.01)

    async def run():
        calls = []

        async def source():
            calls.append("start")
            # An actual task-bound context must survive yields and heartbeat gaps.
            with anyio.CancelScope():
                yield '{"type":"context"}\n'
                await asyncio.sleep(0.05)
                yield '{"type":"token","text":"real provider result"}\n'
                yield '{"type":"done"}\n'

        frames = [json.loads(frame) async for frame in streaming.chat_transport(source())]
        assert sum(f["type"] == "heartbeat" for f in frames) >= 2
        assert [f["type"] for f in frames if f["type"] != "heartbeat"] == [
            "context",
            "token",
            "done",
        ]
        assert calls == ["start"]

    asyncio.run(run())


def test_disconnect_cancels_provider_and_runs_cleanup(monkeypatch):
    monkeypatch.setattr(streaming, "HEARTBEAT_SECONDS", 0.01)

    async def run():
        closed = asyncio.Event()

        async def source():
            try:
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                await asyncio.sleep(0.01)
                closed.set()

        stream = streaming.chat_transport(source())
        assert json.loads(await anext(stream))["type"] == "heartbeat"
        await stream.aclose()
        assert closed.is_set()

    asyncio.run(run())


def test_failure_after_headers_is_reported_without_leaking_details():
    async def run():
        async def source():
            yield '{"type":"context"}\n'
            raise RuntimeError("sensitive-private-value")

        frames = [json.loads(frame) async for frame in streaming.chat_transport(source())]
        assert frames[-1]["type"] == "error" and frames[-1]["code"]
        assert not any(f["type"] == "done" for f in frames)
        assert "sensitive-private-value" not in str(frames)

    asyncio.run(run())
