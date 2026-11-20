"""Keep chat transport alive while a provider is loading; never synthesize answer tokens."""

import asyncio
import json
import logging
import os
import uuid

import anyio

HEARTBEAT_SECONDS = max(0.1, min(30.0, float(os.environ.get("SALY_CHAT_HEARTBEAT_SECONDS", "10"))))
logger = logging.getLogger(__name__)


async def chat_transport(source):
    # A single producer owns the generator's context managers across all yields.
    # The bounded queue prevents unbounded buffering when the browser is slow.
    queue = asyncio.Queue(maxsize=1)

    async def produce():
        try:
            async for frame in source:
                await queue.put(("data", frame))
            await queue.put(("end", None))
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - delivered through the sanitized transport boundary.
            await queue.put(("error", error))
        finally:
            await source.aclose()

    task = asyncio.create_task(produce())
    try:
        while True:
            try:
                kind, value = await asyncio.wait_for(queue.get(), HEARTBEAT_SECONDS)
            except TimeoutError:
                yield json.dumps({"type": "heartbeat"}) + "\n"
                continue
            if kind == "end":
                return
            if kind == "error":
                raise value
            yield value
    except asyncio.CancelledError:
        raise
    except Exception as error:  # noqa: BLE001 - sanitize all failures after HTTP headers were sent.
        reference = uuid.uuid4().hex[:12]
        logger.error("Chat stream interrupted code=%s kind=%s", reference, type(error).__name__)
        yield (
            json.dumps(
                {
                    "type": "error",
                    "code": reference,
                    "detail": "A resposta foi interrompida por uma falha no servidor. Reabra a conversa antes de reenviar. Código: "
                    + reference,
                }
            )
            + "\n"
        )
    finally:
        # Cancel the provider as well as the browser transport; never orphan work.
        with anyio.move_on_after(5, shield=True):
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
