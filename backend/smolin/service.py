import asyncio
import hashlib
import json
import math
import os
import re
import signal
import sys
import tempfile
from pathlib import Path

import httpx
import numpy as np
from fastapi import HTTPException
from sqlalchemy import delete, insert, select, text

from .. import storage as store
from .catalog import documents as catalog
from .formats import classify, safe_name

PIPELINE = "smolin-library-v5"
SEM = asyncio.Semaphore(max(1, min(2, int(os.environ.get("SALY_DOC_WORKERS", "1")))))
TASKS = set()
JOB_TASKS = {}


def storage_cost(doc):
    return max(
        doc.get("reserved_bytes") or 0,
        (doc.get("file_size") or 0)
        + (doc.get("text_size") or 0) * 3
        + (doc.get("chunks") or 0) * 8000,
    )


def upload_limit():
    return max(1, min(512, int(os.environ.get("SALY_SMOLIN_MAX_UPLOAD_MB", "64")))) * 1024 * 1024


class Embeddings:
    def __init__(self):
        self.url = os.environ.get("SALY_EMBEDDING_URL", "").rstrip("/")
        self.key = os.environ.get("SALY_EMBEDDING_API_KEY", "")
        self.model = os.environ.get("SALY_EMBEDDING_MODEL", "")
        self.revision = os.environ.get("SALY_EMBEDDING_REVISION", "")
        self.version = self.model + "@" + self.revision

    @property
    def configured(self):
        return self.url.startswith("https://") and bool(self.model and self.revision)

    async def encode(self, texts):
        if not self.configured:
            raise ValueError("Embeddings não configurados")
        async with httpx.AsyncClient(timeout=40, follow_redirects=False) as c:
            r = await c.post(
                self.url + "/embeddings",
                headers={"Authorization": "Bearer " + self.key},
                json={"model": self.model, "input": texts},
            )
            r.raise_for_status()
            data = r.json()
            if (data.get("revision") or r.headers.get("X-Model-Revision")) != self.revision:
                raise ValueError("O provedor não confirmou a revisão imutável do encoder")
        if data.get("model", self.model) != self.model:
            raise ValueError("Modelo de embeddings incompatível")
        vectors = [
            item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])
        ]
        if len(vectors) != len(texts) or any(
            len(v) != 384 or not all(math.isfinite(x) for x in v) for v in vectors
        ):
            raise ValueError("Dimensão ou vetor inválido")
        return vectors


embedding_provider = Embeddings()


def original(key):
    with store.db() as c:
        r = c.execute(select(store.originals.c.content).where(store.originals.c.id == key)).first()
    if not r:
        raise HTTPException(404, "Original não encontrado")
    return r[0]


def chunk_page(value, size=2800, overlap=350):
    # ~700 tokens, overlap ~12.5%, retaining page boundaries and paragraph endings where possible.
    start = 0
    while start < len(value):
        end = min(start + size, len(value))
        if end < len(value):
            boundary = value.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        content = value[start:end].strip()
        if content:
            yield content
        if end == len(value):
            break
        start = max(start + 1, end - overlap)


def checkpoint(job_id):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise ValueError("Identificador de processamento inválido")
    folder = store.DATA / "smolin-checkpoints"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder / (job_id + ".json")


async def process(key, job_id):
    async with SEM:
        job = store.get("document_jobs", job_id)
        if not job or job.get("cancelled") or job.get("status") == "paused":
            return
        doc = store.get("documents", key)
        if not doc:
            return
        store.save(
            "document_jobs",
            {**job, "status": "processing", "progress": job.get("progress", 0)},
            job_id,
        )
        store.save("documents", {**doc, "status": "processing"}, key)
        try:
            kind = doc.get("kind") or ("pdf" if doc["mime"] == "application/pdf" else "text")
            transcription = job.get("operation") == "transcribe"
            saved = checkpoint(job_id)
            if saved.is_file():
                parsed = json.loads(saved.read_text())
            else:
                raw = original(key)
                store.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
                with tempfile.TemporaryDirectory(prefix="smolin-worker-", dir=store.DATA) as folder:
                    file = Path(folder) / "input.bin"
                    file.write_bytes(raw)
                    file.chmod(0o600)
                    command = (
                        [sys.executable, "-m", "backend.smolin.transcription", str(file)]
                        if transcription
                        else [
                            sys.executable,
                            "-m",
                            "backend.smolin.extract",
                            str(file),
                            str(int(os.environ.get("SALY_MAX_PAGES", "2000"))),
                            "pdf_ocr" if job.get("operation") == "ocr" else kind,
                        ]
                    )
                    environment = {
                        "PATH": os.defpath,
                        "LANG": "C.UTF-8",
                        "OMP_NUM_THREADS": "2",
                        "OPENBLAS_NUM_THREADS": "1",
                    }
                    for name in (
                        "SALY_ZIP_MAX_ENTRIES",
                        "SALY_ZIP_MAX_EXPANDED_MB",
                        "SALY_ZIP_MAX_FILE_MB",
                        "SALY_ZIP_MAX_DEPTH",
                    ):
                        if name in os.environ:
                            environment[name] = os.environ[name]
                    if transcription and os.environ.get("SALY_SMOLIN_WHISPER_MODEL_PATH"):
                        environment["SALY_SMOLIN_WHISPER_MODEL_PATH"] = os.environ[
                            "SALY_SMOLIN_WHISPER_MODEL_PATH"
                        ]
                    proc = await asyncio.create_subprocess_exec(
                        *command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                        env=environment,
                        start_new_session=True,
                    )
                    try:
                        out, _ = await asyncio.wait_for(
                            proc.communicate(), 600 if transcription else 180
                        )
                    except (TimeoutError, asyncio.CancelledError):
                        if proc.returncode is None:
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        await proc.wait()
                        raise
                    if proc.returncode or len(out) > 16 * 1024 * 1024:
                        try:
                            message = json.loads(out).get("error", "Extração não concluída")
                        except (ValueError, AttributeError):
                            message = "Extração não concluída dentro dos limites"
                        raise ValueError(message)
                    parsed = json.loads(out)
                temporary = saved.with_suffix(".tmp")
                temporary.write_text(json.dumps(parsed, ensure_ascii=False))
                temporary.chmod(0o600)
                temporary.replace(saved)
            if transcription:
                old_frames = [p for p in doc.get("pages", []) if p.get("method") != "whisper_local"]
                if doc.get("kind") == "video":
                    parsed["pages"] = sorted(
                        old_frames + parsed["pages"], key=lambda p: p.get("start_seconds", 0)
                    )
                    for number, item in enumerate(parsed["pages"], 1):
                        item["page"] = number
                    parsed["notice"] = (
                        doc.get("interpretation_notice", "") + " " + parsed.get("notice", "")
                    )
            if kind == "archive":
                # Reserve derived storage before incremental writes; concurrent ZIP jobs
                # see this reservation through the existing transaction boundary.
                estimate = (doc.get("file_size") or 0) + sum(
                    len(p["content"].encode()) * 3 + len(list(chunk_page(p["content"]))) * 8000
                    for p in parsed["pages"]
                )
                with store.transaction():
                    used = sum(storage_cost(d) for d in catalog() if d["id"] != key)
                    if used + estimate > int(os.environ.get("SALY_MAX_TOTAL_MB", "200")) * 1024**2:
                        raise ValueError(
                            "Expansão indexada do ZIP excede a capacidade configurada do acervo"
                        )
                    doc = store.save(
                        "documents",
                        {
                            **doc,
                            "reserved_bytes": estimate,
                            "pages": parsed["pages"],
                            "archive_entries": parsed.get("archive_entries", []),
                        },
                        key,
                    )
            current = store.get("document_jobs", job_id)
            if not current.get("indexing_started"):
                with store.transaction():
                    with store.db() as c:
                        c.execute(delete(store.chunks).where(store.chunks.c.document_id == key))
                    current = store.save(
                        "document_jobs",
                        {**current, "indexing_started": True, "processed_pages": 0},
                        job_id,
                    )
            completed_pages = current.get("processed_pages", 0)
            total = len(parsed["pages"])
            empty = []
            count = current.get("chunk_count", 0)
            embedding_error = current.get("embedding_error", False)
            prefs = store.setting("preferences", {})
            use_vectors = (
                kind != "archive"
                and embedding_provider.configured
                and prefs.get("privacy", {}).get("remoteConsent", False)
            )
            for page in parsed["pages"]:
                current = store.get("document_jobs", job_id)
                if not current or current.get("cancelled"):
                    return
                if not page["content"].strip():
                    empty.append(page["page"])
                if page["page"] <= completed_pages:
                    continue
                parts = list(chunk_page(page["content"]))
                vectors = None
                if use_vectors and parts:
                    try:
                        vectors = await embedding_provider.encode(parts)
                    except (httpx.HTTPError, ValueError, KeyError):
                        embedding_error = True
                with store.transaction():
                    with store.db() as c:
                        c.execute(
                            delete(store.chunks).where(
                                store.chunks.c.document_id == key,
                                store.chunks.c.page == page["page"],
                            )
                        )
                    for position, part in enumerate(parts):
                        with store.db() as c:
                            c.execute(
                                insert(store.chunks).values(
                                    id=hashlib.sha256(
                                        f"{key}:{page['page']}:{position}:{part}".encode()
                                    ).hexdigest(),
                                    document_id=key,
                                    page=page["page"],
                                    position=position,
                                    content=part,
                                    embedding=vectors[position] if vectors else None,
                                    embedding_version=embedding_provider.version
                                    if vectors
                                    else None,
                                )
                            )
                        count += 1
                    store.save(
                        "document_jobs",
                        {
                            **current,
                            "progress": round(page["page"] / max(1, total) * 100),
                            "processed_pages": page["page"],
                            "status": "processing",
                            "chunk_count": count,
                            "embedding_error": embedding_error,
                        },
                        job_id,
                    )
                await asyncio.sleep(0)
            current_job = store.get("document_jobs", job_id)
            if not current_job or current_job.get("cancelled") or not store.get("documents", key):
                return
            state = parsed.get("status") or (
                "ocr_required"
                if kind == "pdf" and len(empty) == total
                else "stored_only"
                if not count
                else "partial"
                if empty
                else "ready"
            )
            store.save(
                "documents",
                {
                    **doc,
                    "status": state,
                    "page_count": total,
                    "unit": parsed.get("unit", "page"),
                    "media_info": parsed.get("media_info"),
                    "interpretation_notice": parsed.get(
                        "notice", "Texto extraído do documento; o original é preservado."
                    ),
                    "transcribed": parsed.get("transcribed", False),
                    "pages": parsed["pages"],
                    "archive_entries": parsed.get("archive_entries", []),
                    "reserved_bytes": 0,
                    "title": parsed["title"],
                    "author": parsed["author"],
                    "empty_pages": empty,
                    "chunks": count,
                    "text_size": sum(len(p["content"].encode()) for p in parsed["pages"]),
                    "content": "\n".join(p["content"] for p in parsed["pages"]),
                    "embedding_status": "error"
                    if embedding_error
                    else "ready"
                    if use_vectors and count
                    else "unavailable",
                    "embedding_version": embedding_provider.version if use_vectors else None,
                    "pipeline": PIPELINE,
                },
                key,
            )
            store.save(
                "document_jobs",
                {**store.get("document_jobs", job_id), "status": state, "progress": 100},
                job_id,
            )
            saved.unlink(missing_ok=True)
            from .intelligence import invalidate

            invalidate()
            store.audit("document", "Documento processado: " + key + " · " + state)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - sanitized worker errors only
            reason = (
                str(error)[:300]
                if isinstance(error, ValueError)
                else "Falha interna; tente retomar ou reprocessar."
            )
            if store.get("documents", key):
                store.save(
                    "documents",
                    {
                        **doc,
                        "status": "failed",
                        "interpretation_notice": "O original está preservado; a interpretação não foi concluída. Confira formato, limites e motores locais.",
                    },
                    key,
                )
            if store.get("document_jobs", job_id):
                store.save(
                    "document_jobs",
                    {
                        **store.get("document_jobs", job_id),
                        "status": "failed",
                        "error": reason + " O original continua disponível para download.",
                    },
                    job_id,
                )
            store.audit("document_error", "Falha de processamento: " + key)


def start(key, job_id):
    existing = JOB_TASKS.get(job_id)
    if existing and not existing.done():
        return
    task = asyncio.create_task(process(key, job_id))
    TASKS.add(task)
    JOB_TASKS[job_id] = task

    def finished(completed):
        if JOB_TASKS.get(job_id) is completed:
            JOB_TASKS.pop(job_id, None)

    task.add_done_callback(finished)
    task.add_done_callback(TASKS.discard)


def upload(raw, name):
    with store.transaction():
        return _upload(raw, name)


def _upload(raw, name):
    limit = upload_limit()
    if len(raw) > limit:
        raise HTTPException(413, "Arquivo excede o limite configurado")
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = next((d for d in catalog() if d["sha256"] == digest), None)
    if duplicate:
        return {"id": duplicate["id"], "duplicate": True, "status": duplicate["status"]}
    if len(catalog()) >= int(os.environ.get("SALY_MAX_DOCUMENTS", "50")):
        raise HTTPException(413, "Acervo atingiu o limite de documentos")
    filename = safe_name(name)
    try:
        mime, kind = classify(raw, filename)
        if filename.lower().endswith(".pdf") and kind != "pdf":
            raise ValueError("PDF inválido")
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(
            422,
            "Conteúdo inválido para o formato; texto precisa ser UTF-8/UTF-16 válido e PDF precisa ter assinatura PDF",
        ) from None
    used = sum(storage_cost(d) for d in catalog())
    if used + len(raw) > int(os.environ.get("SALY_MAX_TOTAL_MB", "200")) * 1024 * 1024:
        raise HTTPException(413, "Capacidade configurada do acervo atingida")
    doc = store.save(
        "documents",
        {
            "name": filename,
            "mime": mime,
            "kind": kind,
            "unit": "page" if kind == "pdf" else "section",
            "interpretation_notice": "Arquivo preservado para download; este formato não possui interpretador instalado."
            if kind == "binary"
            else "Aguardando interpretação local.",
            "sha256": digest,
            "file_size": len(raw),
            "status": "stored_only" if kind == "binary" else "queued",
            "page_count": 0,
            "chunks": 0,
            "pipeline": PIPELINE,
            "content": "",
            "pages": [],
            "embedding_status": "unavailable",
        },
    )
    with store.db() as c:
        c.execute(insert(store.originals).values(id=doc["id"], content=raw))
    if kind == "binary":
        store.audit("document", "Arquivo privado armazenado sem interpretação: " + doc["id"])
        return {"id": doc["id"], "duplicate": False, "status": "stored_only"}
    job = store.save(
        "document_jobs",
        {"document_id": doc["id"], "status": "queued", "progress": 0, "cancelled": False},
    )
    store.audit("document", "Original privado recebido: " + doc["id"])
    return {"id": doc["id"], "job_id": job["id"], "duplicate": False, "status": "queued"}


def source_url(doc, page):
    original = f"/api/knowledge/{doc['id']}/original"
    item = next((p for p in doc.get("pages", []) if p["page"] == page), {})
    if "entry_index" in item:
        return f"/api/knowledge/{doc['id']}/entries/{item['entry_index']}/original#page={item['source_page']}"
    return (
        original + f"#t={item['start_seconds']}"
        if "start_seconds" in item
        else original + f"#page={page}"
    )


def source_metadata(doc, page):
    item = next((p for p in doc.get("pages", []) if p["page"] == page), {})
    return {
        "title": item.get("source_title") or doc.get("title") or doc.get("name"),
        "author": item.get("source_author") or doc.get("author") or None,
        **{
            key: item[key]
            for key in (
                "start_seconds",
                "end_seconds",
                "label",
                "chapter",
                "method",
                "archive_path",
                "source_page",
                "entry_index",
            )
            if key in item
        },
    }


def lexical(query, limit=8, document_id=None):
    tokens = re.findall(r"\w+", query, re.UNICODE)[:20]
    if not tokens:
        return []
    with store.db() as c:
        if store.engine.dialect.name == "sqlite":
            q = " OR ".join('"' + t + '"' for t in tokens)
            rows = (
                c.execute(
                    text(
                        "SELECT c.* FROM smolin_fts f JOIN document_chunks c ON c.id=f.id WHERE smolin_fts MATCH :q AND (:doc IS NULL OR c.document_id = :doc) ORDER BY rank LIMIT :lim"
                    ),
                    {"q": q, "lim": limit, "doc": document_id},
                )
                .mappings()
                .all()
            )
        else:
            rows = (
                c.execute(
                    text(
                        "SELECT * FROM document_chunks WHERE to_tsvector('portuguese',content) @@ plainto_tsquery('portuguese',:q) AND (:doc IS NULL OR document_id = :doc) LIMIT :lim"
                    ),
                    {"q": query, "lim": limit, "doc": document_id},
                )
                .mappings()
                .all()
            )
    results = []
    for r in rows:
        doc = store.get("documents", r["document_id"])
        if doc and doc.get("status") in ("ready", "partial", "legacy_text_only"):
            results.append(
                {
                    "chunk_id": r["id"],
                    "id": doc["id"],
                    "name": doc["name"],
                    "page": r["page"] or None,
                    "position": r["position"],
                    "content": r["content"],
                    "source": "smolin",
                    "url": source_url(doc, r["page"]),
                    **source_metadata(doc, r["page"]),
                }
            )
    return results


async def search(query, document_id=None, remote_allowed=True):
    results = lexical(query, document_id=document_id)
    if os.environ.get("SALY_LOCAL_LSA", "1") == "1":
        from .intelligence import semantic

        try:
            similar, _ = await asyncio.to_thread(semantic, query, document_id)
            # Keep lexical matches; add real local latent associations, clearly labelled.
            for row in similar:
                if row["id"] in {result["chunk_id"] for result in results}:
                    continue
                doc = store.get("documents", row["document_id"])
                if doc and doc.get("status") in {"ready", "partial", "legacy_text_only"}:
                    results.append(
                        {
                            "chunk_id": row["id"],
                            "id": doc["id"],
                            "name": doc["name"],
                            "page": row["page"],
                            "position": row["position"],
                            "content": row["content"],
                            "source": "smolin",
                            "url": source_url(doc, row["page"]),
                            "retrieval": "local_lsa",
                            "semantic_score": row["semantic_score"],
                            **source_metadata(doc, row["page"]),
                        }
                    )
        except (OSError, ValueError, np.linalg.LinAlgError):
            store.audit("lsa_error", "Índice LSA indisponível; busca textual preservada")
    if (
        remote_allowed
        and embedding_provider.configured
        and store.setting("preferences", {}).get("privacy", {}).get("remoteConsent", False)
    ):
        try:
            vector = (await embedding_provider.encode([query]))[0]
            if store.engine.dialect.name == "postgresql":
                with store.db() as c:
                    rows = (
                        c.execute(
                            select(store.chunks)
                            .where(store.chunks.c.embedding_version == embedding_provider.version)
                            .where(
                                store.chunks.c.document_id == document_id if document_id else True
                            )
                            .order_by(store.chunks.c.embedding.cosine_distance(vector))
                            .limit(8)
                        )
                        .mappings()
                        .all()
                    )
            else:
                with store.db() as c:
                    rows = (
                        c.execute(
                            select(store.chunks)
                            .where(store.chunks.c.embedding_version == embedding_provider.version)
                            .where(
                                store.chunks.c.document_id == document_id if document_id else True
                            )
                        )
                        .mappings()
                        .all()
                    )

                def similarity(r):
                    v = r["embedding"]
                    return sum(a * b for a, b in zip(vector, v, strict=True)) / (
                        math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(a * a for a in v))
                        or 1
                    )

                rows = sorted(rows, key=similarity, reverse=True)[:8]
            for row in rows:
                if row["id"] in [r["chunk_id"] for r in results]:
                    continue
                d = store.get("documents", row["document_id"])
                if (
                    d
                    and (not document_id or d["id"] == document_id)
                    and d.get("status") in ("ready", "partial", "legacy_text_only")
                ):
                    results.append(
                        {
                            "chunk_id": row["id"],
                            "id": d["id"],
                            "name": d["name"],
                            "page": row["page"],
                            "position": row["position"],
                            "content": row["content"],
                            "source": "smolin",
                            "url": source_url(d, row["page"]),
                            **source_metadata(d, row["page"]),
                        }
                    )
        except (httpx.HTTPError, ValueError, KeyError):
            store.audit(
                "embedding_error", "Busca vetorial indisponível; resultados textuais preservados"
            )
    return results[:8]


def delete_document(key):
    from .intelligence import invalidate

    invalidate()
    for job in store.all_records("document_jobs"):
        if job["document_id"] == key:
            checkpoint(job["id"]).unlink(missing_ok=True)
            checkpoint(job["id"]).with_suffix(".tmp").unlink(missing_ok=True)
            store.save(
                "document_jobs", {**job, "cancelled": True, "status": "cancelled"}, job["id"]
            )
            task = JOB_TASKS.get(job["id"])
            if task:
                task.get_loop().call_soon_threadsafe(task.cancel)
    with store.db() as connection:
        connection.execute(delete(store.config).where(store.config.c.id == "pdf-reading:" + key))
    # FK cascades remove original, chunks, vectors; SQLite triggers remove FTS entries.
    store.remove("documents", key)
    for message in store.all_records("messages"):
        if key in [s.get("id") for s in message.get("sources", [])]:
            store.save(
                "messages",
                {
                    **message,
                    "content": "[Resposta derivada de documento excluído removida.]",
                    "sources": [],
                    "verification": None,
                },
                message["id"],
            )
    store.set_setting("context_epoch", store.setting("context_epoch", 0) + 1)
    for approval in store.all_records("agent_approvals"):
        if approval["status"] == "pending":
            store.save("agent_approvals", {**approval, "status": "expired"}, approval["id"])
    store.audit("document", "Documento, original e índices excluídos: " + key)
