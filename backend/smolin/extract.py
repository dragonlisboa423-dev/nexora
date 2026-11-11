"""Isolated PDF text extraction. Input is never executable application code."""

import json
import resource
import sys

from pypdf import PdfReader

if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    try:
        reader = PdfReader(sys.argv[1])
        if reader.is_encrypted or len(reader.pages) > int(sys.argv[2]):
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
        print(
            json.dumps(
                {
                    "pages": pages,
                    "title": str(meta.get("/Title", ""))[:500],
                    "author": str(meta.get("/Author", ""))[:500],
                },
                ensure_ascii=False,
            )
        )
    except Exception:  # noqa: BLE001 - sanitize errors at the untrusted operation boundary
        print(json.dumps({"error": "PDF inválido, protegido ou limite de processamento excedido"}))
        raise SystemExit(1)
