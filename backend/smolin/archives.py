"""Bounded ZIP ingestion. Paths are metadata only, never filesystem destinations."""

import io
import os
import re
import stat
import struct
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from .formats import classify


def limit(name, default, ceiling):
    return max(1, min(int(os.environ.get(name, default)), ceiling))


def preflight(source):
    """Bound the central directory BEFORE ZipFile allocates an object per entry."""
    if isinstance(source, bytes):
        size = len(source)
        tail = source[-65557:]
    else:
        with open(source, "rb") as handle:
            size = handle.seek(0, 2)
            handle.seek(max(0, size - 65557))
            tail = handle.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or offset + 22 > len(tail):
        raise ValueError("ZIP sem diretório central válido")
    _, disk, directory_disk, disk_count, count, directory_size, directory_offset, comment = (
        struct.unpack_from("<4s4H2LH", tail, offset)
    )
    if offset + 22 + comment != len(tail) or disk or directory_disk or count != disk_count:
        raise ValueError("ZIP multipartes ou diretório central inválido")
    if count == 65535 or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
        raise ValueError("ZIP64 não suportado dentro dos limites desta importação")
    if count > limit("SALY_ZIP_MAX_ENTRIES", 200, 1000):
        raise ValueError("ZIP excede limite de quantidade de arquivos")
    if (
        directory_size > limit("SALY_ZIP_MAX_ENTRIES", 200, 1000) * 8192
        or directory_offset + directory_size > size
    ):
        raise ValueError("Diretório central do ZIP excede o limite de metadados")


def inspect(archive):
    entries = archive.infolist()
    count = limit("SALY_ZIP_MAX_ENTRIES", 200, 1000)
    expanded = limit("SALY_ZIP_MAX_EXPANDED_MB", 128, 256) * 1024**2
    single = limit("SALY_ZIP_MAX_FILE_MB", 32, 64) * 1024**2
    depth = limit("SALY_ZIP_MAX_DEPTH", 8, 16)
    if len(entries) > count or sum(i.file_size for i in entries) > expanded:
        raise ValueError("ZIP excede limite de quantidade ou tamanho expandido")
    names = set()
    for item in entries:
        name = item.orig_filename
        if (
            len(name) > 500
            or "\\" in name
            or "\x00" in name
            or name.startswith("/")
            or re.match(r"^[A-Za-z]:", name)
            or any(x in {"", "..", "."} for x in (name[:-1] if item.is_dir() else name).split("/"))
            or len(PurePosixPath(name).parts) > depth
            or not name
        ):
            raise ValueError("ZIP contém caminho inseguro ou profundidade excessiva")
        normalized = name.casefold().rstrip("/")
        if normalized in names:
            raise ValueError("ZIP contém caminhos duplicados/ambíguos")
        names.add(normalized)
        mode = item.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
            raise ValueError("ZIP contém link ou arquivo especial")
        if item.flag_bits & 1:
            raise ValueError("ZIP criptografado: senha não é suportada")
        if item.file_size > single or item.file_size > max(1, item.compress_size) * 100:
            raise ValueError("ZIP excede limite por arquivo ou taxa de compressão segura")
        if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ValueError("Compressão ZIP não suportada com segurança")
    files = {item.filename.casefold() for item in entries if not item.is_dir()}
    for item in entries:
        parts = item.filename.casefold().rstrip("/").split("/")
        if any("/".join(parts[:n]) in files for n in range(1, len(parts))):
            raise ValueError("ZIP contém conflito entre arquivo e caminho de pasta")
    return entries


def read_entry(archive, item):
    maximum = limit("SALY_ZIP_MAX_FILE_MB", 32, 64) * 1024**2
    with archive.open(item) as source:
        raw = source.read(min(item.file_size, maximum) + 1)
        if len(raw) != item.file_size or len(raw) > maximum or source.read(1):
            raise ValueError("Tamanho expandido do ZIP inconsistente")
    return raw


EXECUTABLE = {
    ".exe",
    ".dll",
    ".so",
    ".sh",
    ".bat",
    ".cmd",
    ".ps1",
    ".com",
    ".msi",
    ".apk",
    ".appimage",
    ".py",
    ".js",
    ".jar",
    ".wasm",
}
SUPPORTED = {
    "pdf",
    "text",
    "html",
    "word",
    "image",
    "spreadsheet",
    "opendocument",
    "epub",
    "slides",
}


def extract_archive(path, maximum):
    from .extract import extract

    preflight(path)
    pages, manifest = [], []
    remaining = 2_000_000
    with (
        zipfile.ZipFile(path) as archive,
        tempfile.TemporaryDirectory(prefix="saly-zip-entries-") as work,
    ):
        entries = inspect(archive)  # Validate whole directory BEFORE reading a single payload.
        for index, item in enumerate(entries):
            entry = {
                "index": index,
                "path": item.filename,
                "size": item.file_size,
                "directory": item.is_dir(),
                "status": "directory" if item.is_dir() else "unsupported",
                "pages": 0,
            }
            manifest.append(entry)
            if item.is_dir():
                continue
            if Path(item.filename).suffix.lower() in EXECUTABLE:
                entry.update(
                    status="blocked",
                    notice="Programa preservado apenas dentro do ZIP; não executado nem indexado.",
                )
                continue
            if remaining <= 0 or len(pages) >= maximum:
                entry.update(status="partial", notice="Limite agregado de texto/páginas atingido.")
                continue
            try:
                raw = read_entry(archive, item)
                mime, kind = classify(raw, item.filename)
                entry.update(mime=mime, kind=kind)
                if kind not in SUPPORTED:
                    entry["notice"] = (
                        "Formato armazenado no ZIP; interpretação não disponível (ZIPs aninhados não são expandidos)."
                    )
                    continue
                target = Path(work) / str(index)  # NEVER use an uploaded path.
                target.write_bytes(raw)
                try:
                    parsed = extract(str(target), maximum - len(pages), kind)
                finally:
                    target.unlink(missing_ok=True)
                entry["status"] = parsed.get("status", "ready")
                if parsed.get("notice"):
                    entry["notice"] = parsed["notice"][:500]
                for page in parsed["pages"]:
                    if len(pages) >= maximum or remaining <= 0:
                        entry["status"] = "partial"
                        break
                    content = page["content"][:remaining]
                    if len(content) < len(page["content"]) or not content.strip():
                        entry["status"] = "partial"
                    remaining -= len(content)
                    pages.append(
                        {
                            **page,
                            "page": len(pages) + 1,
                            "source_page": page["page"],
                            "source_title": parsed.get("title", ""),
                            "source_author": parsed.get("author", ""),
                            "archive_path": item.filename,
                            "entry_index": index,
                            "content": content,
                            "label": item.filename + " · página " + str(page["page"]),
                        }
                    )
                    entry["pages"] += 1
            except Exception as error:  # noqa: BLE001 - isolate each untrusted parser within worker CPU/AS/wall limits.
                entry.update(
                    status="error",
                    notice=str(error)[:250]
                    if isinstance(error, ValueError)
                    else "Arquivo incompatível/corrompido ou motor ausente; original preservado no ZIP.",
                )
    complete = all(e["status"] in {"ready", "directory"} for e in manifest)
    return {
        "pages": pages,
        "title": "",
        "author": "",
        "unit": "section",
        "archive_entries": manifest,
        "status": "ready" if complete else "partial",
        "notice": "Conteúdo interno indexado por arquivo e página. Veja os estados individuais; imagens usam OCR, não compreensão visual generativa.",
    }


def original_entry(raw, index):
    preflight(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = inspect(archive)
        if index < 0 or index >= len(entries) or entries[index].is_dir():
            raise ValueError("Arquivo interno não encontrado")
        item = entries[index]
        if Path(item.filename).suffix.lower() in EXECUTABLE:
            raise ValueError(
                "Download individual de programa bloqueado; o ZIP original permanece disponível"
            )
        content = read_entry(archive, item)
        mime, kind = classify(content, item.filename)
        if kind == "html":
            mime = "application/octet-stream"
        return content, Path(item.filename).name, mime
