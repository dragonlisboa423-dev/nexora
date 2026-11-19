"""Resource-limited extraction in a separate process; no uploaded program is executed."""

import json
import resource
import sys
from pathlib import Path

from pypdf import PdfReader

from .formats import decode_text, extract_package, html_text
from .media_text import extract_media, ocr


def extract(path, maximum, kind):
    if kind == "archive":
        from .archives import extract_archive
        return extract_archive(path, maximum)
    if kind == "pdf_ocr":
        from .ocr_pdf import extract_pdf_ocr

        return extract_pdf_ocr(path, maximum)
    if kind == "pdf":
        reader = PdfReader(path)
        if reader.is_encrypted or len(reader.pages) > maximum:
            raise ValueError(
                "PDF protegido por senha"
                if reader.is_encrypted
                else f"PDF com {len(reader.pages)} páginas excede o limite configurado de {maximum}; o leitor original continua disponível"
            )
        chapters = []

        def outline(items, depth=0):
            if depth > 10:
                return
            for item in items[:1000]:
                if isinstance(item, list):
                    outline(item, depth + 1)
                else:
                    try:
                        number = reader.get_destination_page_number(item)
                        if number is not None and number >= 0:
                            chapters.append((number + 1, str(item.title)[:200]))
                    except (ValueError, AttributeError, KeyError):
                        pass

        outline(reader.outline)
        chapters.sort(key=lambda pair: pair[0])
        pages = []
        total = 0
        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""
            total += len(content)
            if total > 2_000_000:
                raise ValueError("Texto excede o limite")
            labels = [label for start, label in chapters if start <= number]
            pages.append(
                {"page": number, "content": content, **({"chapter": labels[-1]} if labels else {})}
            )
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
    except Exception as error:  # noqa: BLE001 - no input/parser secrets in worker output
        print(
            json.dumps(
                {
                    "error": str(error)[:250]
                    if isinstance(error, ValueError)
                    else "Arquivo corrompido/incompatível, motor ausente ou limite de processamento; original preservado."
                }
            )
        )
        raise SystemExit(1)
