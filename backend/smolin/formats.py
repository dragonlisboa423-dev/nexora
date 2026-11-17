"""File classification and bounded text extraction; originals are never executed."""

import codecs
import mimetypes
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".rs",
    ".go",
    ".rb",
    ".sh",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".log",
    ".srt",
    ".vtt",
    ".tex",
    ".rtf",
    ".svg",
}
PACKAGES = {
    ".docx": "word",
    ".xlsx": "spreadsheet",
    ".pptx": "slides",
    ".odt": "opendocument",
    ".ods": "opendocument",
    ".odp": "opendocument",
    ".epub": "epub",
}


def safe_name(name):
    value = Path(name.replace("\\", "/")).name
    value = "".join(c for c in value if c.isprintable())[:200].strip()
    return value or "arquivo"


def decode_text(raw):
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    if "\x00" in text or len(text) > 2_000_000:
        raise ValueError("Texto binário ou extenso demais")
    return text


def classify(raw, name):
    ext = Path(name).suffix.lower()
    if ext in TEXT_EXTENSIONS and raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        decode_text(raw)
        return "text/plain", "html" if ext in {".html", ".htm", ".svg"} else "text"

    if raw.lstrip().startswith(b"%PDF-"):
        return "application/pdf", "pdf"
    if raw.startswith(
        (b"\x89PNG\r\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM", b"II*\0", b"MM\0*")
    ) or (raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"):
        mime = (
            "image/png"
            if raw.startswith(b"\x89PNG")
            else "image/jpeg"
            if raw.startswith(b"\xff\xd8")
            else "image/gif"
            if raw.startswith(b"GIF")
            else "image/bmp"
            if raw.startswith(b"BM")
            else "image/webp"
            if raw[:4] == b"RIFF"
            else "image/tiff"
        )
        return mime, "image"
    if (len(raw) > 12 and raw[4:8] == b"ftyp") or raw.startswith(b"\x1aE\xdf\xa3"):
        if ext in {".m4a", ".m4b"}:
            return "audio/mp4", "audio"
        return ("video/webm" if raw.startswith(b"\x1aE") else "video/mp4"), "video"
    if (
        raw[:3] == b"ID3"
        or (len(raw) > 2 and raw[0] == 255 and raw[1] & 224 == 224)
        or raw.startswith((b"OggS", b"fLaC"))
        or (raw[:4] == b"RIFF" and raw[8:12] == b"WAVE")
    ):
        return (mimetypes.guess_type(name)[0] or "audio/mpeg"), "audio"
    if ext in PACKAGES and raw.startswith(b"PK"):
        return (mimetypes.guess_type(name)[0] or "application/zip"), PACKAGES[ext]
    if ext in TEXT_EXTENSIONS:
        decode_text(raw)
        return (
            "text/plain" if ext not in {".md", ".markdown"} else "text/markdown"
        ), "html" if ext in {".html", ".htm", ".svg"} else "text"
    if ext == ".zip" and raw.startswith(b"PK"):
        return "application/zip", "archive"
    return "application/octet-stream", "binary"


class VisibleHtml(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        if tag in {"p", "br", "div", "h1", "h2", "h3", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def html_text(value):
    parser = VisibleHtml()
    parser.feed(value)
    return "".join(parser.parts).strip()


def xml(raw):
    compact = raw.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in compact or b"<!ENTITY" in compact:
        raise ValueError("XML com entidades não permitido")
    return ET.fromstring(raw)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def paragraphs(raw):
    root = xml(raw)
    return "\n".join("".join(p.itertext()) for p in root.iter() if local(p.tag) in {"p", "h"})


def extract_package(path, kind, max_pages):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 3000 or sum(e.file_size for e in entries) > 100 * 1024 * 1024:
            raise ValueError("Arquivo compactado acima do limite de expansão")
        if any(
            e.file_size > 15 * 1024 * 1024
            or (e.file_size > 100000 and e.file_size > max(1, e.compress_size) * 250)
            for e in entries
        ):
            raise ValueError("Expansão compactada insegura")
        names = set(archive.namelist())

        def read(name):
            return archive.read(name)

        def natural(name):
            return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]

        pages = []
        title = author = ""
        epub_spine = False
        if kind == "word":
            parts = [("Documento", "word/document.xml")]
        elif kind == "slides":
            parts = [
                (name, name)
                for name in sorted(names, key=natural)
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ]
        elif kind == "spreadsheet":
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = ["".join(e.itertext()) for e in xml(read("xl/sharedStrings.xml"))]
            for name in sorted(names, key=natural):
                if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name):
                    continue
                rows = []
                for row in xml(read(name)).iter():
                    if local(row.tag) != "row":
                        continue
                    cells = []
                    for cell in row:
                        values = [e.text or "" for e in cell.iter() if local(e.tag) in {"v", "t"}]
                        if cell.attrib.get("t") == "s" and values:
                            values = [shared[int(values[0])]]
                        formula = next((e.text for e in cell if local(e.tag) == "f"), None)
                        cells.append(
                            (
                                "Fórmula não recalculada: " + formula + "; valor salvo: "
                                if formula
                                else ""
                            )
                            + " ".join(values)
                        )
                    rows.append("\t".join(cells))
                pages.append({"page": len(pages) + 1, "label": name, "content": "\n".join(rows)})
            parts = []
        elif kind == "opendocument":
            parts = [("Documento", "content.xml")]
        elif kind == "epub":
            parts = []
            if "META-INF/container.xml" in names:
                container = xml(read("META-INF/container.xml"))
                rootfile = next(
                    (
                        e.attrib.get("full-path")
                        for e in container.iter()
                        if local(e.tag) == "rootfile"
                    ),
                    None,
                )
                if not rootfile or rootfile not in names:
                    raise ValueError("EPUB sem pacote OPF válido")
                package = xml(read(rootfile))
                title = next((e.text or "" for e in package.iter() if local(e.tag) == "title"), "")[
                    :500
                ]
                author = next(
                    (e.text or "" for e in package.iter() if local(e.tag) == "creator"), ""
                )[:500]
                manifest = {
                    e.attrib.get("id"): e.attrib for e in package.iter() if local(e.tag) == "item"
                }
                for item in package.iter():
                    if local(item.tag) != "itemref" or item.attrib.get("linear") == "no":
                        continue
                    entry = manifest.get(item.attrib.get("idref"), {})
                    href = entry.get("href", "").split("#")[0]
                    name = posixpath.normpath(posixpath.join(posixpath.dirname(rootfile), href))
                    if ":" in href or name.startswith(("/", "../")) or name not in names:
                        raise ValueError("EPUB com referência externa/ausente no spine")
                    if entry.get("media-type") in {"application/xhtml+xml", "text/html"}:
                        parts.append((name, name))
                epub_spine = bool(parts)
                if not parts:
                    raise ValueError("EPUB sem capítulos legíveis no spine")
            else:
                parts = [
                    (name, name)
                    for name in sorted(names, key=natural)
                    if name.lower().endswith((".html", ".htm", ".xhtml"))
                ]
        else:
            parts = []
            pages = [
                {
                    "page": 1,
                    "label": "Índice do ZIP",
                    "content": "Arquivos do pacote (conteúdo interno não interpretado):\n"
                    + "\n".join(e.filename for e in entries),
                }
            ]
        if len(parts) > max_pages or len(pages) > max_pages:
            raise ValueError("Seções acima do limite")
        for label, name in parts:
            raw = read(name)
            content = html_text(raw.decode("utf-8-sig")) if kind == "epub" else paragraphs(raw)
            if kind == "epub":
                heading = re.search(
                    r"<(?:h1|h2|title)\b[^>]*>(.*?)</(?:h1|h2|title)>",
                    raw.decode("utf-8-sig"),
                    re.IGNORECASE | re.DOTALL,
                )
                if heading:
                    label = html_text(heading.group(1))[:200] or label
            pages.append({"page": len(pages) + 1, "label": label, "content": content})
        if sum(len(p["content"]) for p in pages) > 2_000_000:
            raise ValueError("Texto acima do limite")
        return {
            "pages": pages,
            "title": title,
            "author": author,
            "unit": "section",
            "notice": "EPUB: capítulos na ordem declarada no spine; leitura textual, original disponível para download."
            if epub_spine
            else "Texto extraído sem executar scripts/macros. Sem spine EPUB válido, seções seguem os nomes dos arquivos; diagramação original no download.",
        }
