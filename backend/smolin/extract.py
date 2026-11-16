"""Resource-limited extraction in a separate process; no uploaded program is executed."""

import json
import resource
import sys
from pathlib import Path

from pypdf import PdfReader

from .formats import decode_text, extract_package, html_text
from .media_text import extract_media, ocr


def extract(path, maximum, kind):
    if kind == "pdf":
        reader = PdfReader(path)
        if reader.is_encrypted or len(reader.pages) > maximum:
            raise ValueError("PDF protegido ou extenso demais")
        pages = []
        total = 0
        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""
            total += len(content)
            if total > 2_000_000:
                raise ValueError("Texto excede o limite")
            pages.append({"page": number, "content": content})
        meta = reader.metadata or {}
        return {
            "pages": pages,
            "title": str(meta.get("/Title", ""))[:500],
            "author": str(meta.get("/Author", ""))[:500],
            "unit": "page",
        }
    if kind in {"audio", "video"}:
        return extract_media(path, kind, Path(path).parent)
    if kind == "image":
        text, notice = ocr(path, Path(path).parent)
        return {
            "pages": [{"page": 1, "content": text, "method": "ocr"}],
            "title": "",
            "author": "",
            "unit": "image",
            "notice": notice,
            "status": "ready" if text else "stored_only",
        }
    if kind in {"word", "slides", "spreadsheet", "opendocument", "epub", "archive"}:
        return extract_package(path, kind, maximum)
    value = decode_text(Path(path).read_bytes())
    if kind == "html":
        value = html_text(value)
    return {"pages": [{"page": 1, "content": value}], "title": "", "author": "", "unit": "section"}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    try:
        print(
            json.dumps(
                extract(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "pdf"),
                ensure_ascii=False,
            )
        )
    except Exception:  # noqa: BLE001 - no input/parser secrets in worker output
        print(
            json.dumps(
                {
                    "error": "Não foi possível extrair conteúdo dentro dos limites; o original permanece disponível."
                }
            )
        )
        raise SystemExit(1)
