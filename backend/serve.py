"""Start from the same private configuration used by CLI and ASGI."""

import os

import uvicorn

from . import storage  # noqa: F401 - initializes dotenv without overriding injected bindings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=os.environ.get("SALY_HOST", "127.0.0.1"),
        port=int(os.environ.get("SALY_PORT", os.environ.get("PORT", "8000"))),
    )
