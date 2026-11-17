"""Explicit CPU-expensive PDF OCR, limited pages, one raster at a time; original untouched."""

import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

from .media_text import ENV, ocr


def extract_pdf_ocr(path, maximum):
    if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
        raise ValueError("OCR de PDF requer Poppler (pdftoppm) e Tesseract instalados")
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("PDF protegido: abra o original com senha num leitor externo")
    if len(reader.pages) > min(maximum, 40):
        raise ValueError(
            "OCR limitado a 40 páginas por operação para preservar CPU/RAM; divida o PDF"
        )
    pages = []
    for number, page in enumerate(reader.pages, 1):
        content = page.extract_text() or ""
        method = "pdf_text"
        if not content.strip():
            output = Path(path).parent / "pdf-ocr"
            subprocess.run(
                [
                    "pdftoppm",
                    "-f",
                    str(number),
                    "-l",
                    str(number),
                    "-singlefile",
                    "-scale-to",
                    "2000",
                    "-png",
                    str(path),
                    str(output),
                ],
                timeout=30,
                check=True,
                capture_output=True,
                env=ENV,
            )
            content, _ = ocr(output.with_suffix(".png"), Path(path).parent)
            output.with_suffix(".png").unlink(missing_ok=True)
            method = "pdf_ocr_tesseract"
        pages.append({"page": number, "content": content, "method": method})
        if sum(len(p["content"]) for p in pages) > 2_000_000:
            raise ValueError("Texto OCR acima do limite de dois milhões de caracteres")
    meta = reader.metadata or {}
    return {
        "pages": pages,
        "title": str(meta.get("/Title", ""))[:500],
        "author": str(meta.get("/Author", ""))[:500],
        "unit": "page",
        "notice": "OCR local opcional: revise erros. Original preservado; limite de 40 páginas por operação.",
    }
