import asyncio
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, insert, select, text

from .. import storage as store

PIPELINE = "smolin-pages-v2"
SEM = asyncio.Semaphore(max(1, min(2, int(os.environ.get("SALY_DOC_WORKERS", "1")))))
TASKS = set()
JOB_TASKS = {}


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


async def process(key, job_id):
    async with SEM:
        job = store.get("document_jobs", job_id)
        if not job or job.get("cancelled"):
            return
        doc = store.get("documents", key)
        if not doc:
            return
        store.save("document_jobs", {**job, "status": "processing", "progress": 0}, job_id)
        store.save("documents", {**doc, "status": "processing"}, key)
        try:
            raw = original(key)
            if doc["mime"] == "application/pdf":
                store.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
                with tempfile.TemporaryDirectory(dir=store.DATA) as folder:
                    file = Path(folder) / "input.pdf"
                    file.write_bytes(raw)
                    file.chmod(0o600)
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "-m",
                        "backend.smolin.extract",
                        str(file),
                        str(int(os.environ.get("SALY_MAX_PAGES", "500"))),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    try:
                        out, _ = await asyncio.wait_for(proc.communicate(), 40)
                    except (TimeoutError, asyncio.CancelledError):
                        proc.kill()
                        await proc.wait()
                        raise
                    if proc.returncode:
                        raise ValueError("PDF inválido ou limite de extração excedido")
                    parsed = json.loads(out)
            else:
                parsed = {
                    "pages": [{"page": 1, "content": raw.decode("utf-8-sig")}],
                    "title": doc["name"],
                    "author": "",
                }
            with store.db() as c:
                c.execute(delete(store.chunks).where(store.chunks.c.document_id == key))
            total = len(parsed["pages"])
            empty = []
            count = 0
            embedding_error = False
            prefs = store.setting("preferences", {})
            use_vectors = embedding_provider.configured and prefs.get("privacy", {}).get(
                "remoteConsent", False
            )
            for page in parsed["pages"]:
                current = store.get("document_jobs", job_id)
                if not current or current.get("cancelled"):
                    return
                if not page["content"].strip():
                    empty.append(page["page"])
                parts = list(chunk_page(page["content"]))
                vectors = None
                if use_vectors and parts:
                    try:
                        vectors = await embedding_provider.encode(parts)
                    except (httpx.HTTPError, ValueError, KeyError):
                        embedding_error = True
                with store.db() as c:
                    for position, part in enumerate(parts):
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
                                embedding_version=embedding_provider.version if vectors else None,
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
                    },
                    job_id,
                )
                await asyncio.sleep(0)
            current_job = store.get("document_jobs", job_id)
            if not current_job or current_job.get("cancelled") or not store.get("documents", key):
                return
            state = "ocr_required" if len(empty) == total else "partial" if empty else "ready"
            store.save(
                "documents",
                {
                    **doc,
                    "status": state,
                    "page_count": total,
                    "pages": parsed["pages"],
                    "title": parsed["title"],
                    "author": parsed["author"],
                    "empty_pages": empty,
                    "chunks": count,
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
            store.audit("document", "Documento processado: " + key + " · " + state)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - sanitize errors at the untrusted operation boundary
            if store.get("documents", key):
                store.save("documents", {**doc, "status": "failed"}, key)
            if store.get("document_jobs", job_id):
                store.save(
                    "document_jobs",
                    {
                        **store.get("document_jobs", job_id),
                        "status": "failed",
                        "error": "Não foi possível processar o arquivo dentro dos limites.",
                    },
                    job_id,
                )
            store.audit("document_error", "Falha de processamento: " + key)


def start(key, job_id):
    task = asyncio.create_task(process(key, job_id))
    TASKS.add(task)
    JOB_TASKS[job_id] = task
    task.add_done_callback(lambda _: JOB_TASKS.pop(job_id, None))
    task.add_done_callback(TASKS.discard)


def upload(raw, name):
    limit = int(os.environ.get("SALY_MAX_UPLOAD_MB", "10")) * 1024 * 1024
    if len(raw) > limit:
        raise HTTPException(413, "Arquivo excede o limite configurado")
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = next((d for d in store.all_records("documents") if d["sha256"] == digest), None)
    if duplicate:
        return {"id": duplicate["id"], "duplicate": True, "status": duplicate["status"]}
    if len(store.all_records("documents")) >= int(os.environ.get("SALY_MAX_DOCUMENTS", "50")):
        raise HTTPException(413, "Acervo atingiu o limite de documentos")
    filename = Path(name).name[:200]
    if raw.lstrip().startswith(b"%PDF-"):
        mime = "application/pdf"
    elif filename.lower().endswith((".txt", ".md")):
        try:
            if b"\x00" in raw:
                raise ValueError("binário")
            decoded = raw.decode("utf-8-sig")
            if len(decoded) > 2_000_000:
                raise ValueError("Texto excede o limite")
        except (UnicodeDecodeError, ValueError):
            raise HTTPException(422, "Texto precisa ser UTF-8 válido") from None
        mime = "text/markdown" if filename.lower().endswith(".md") else "text/plain"
    else:
        raise HTTPException(422, "Conteúdo não corresponde a PDF ou texto UTF-8 suportado")
    used = sum(
        d.get("file_size", 0) + len(d.get("content", "").encode()) * 3 + d.get("chunks", 0) * 8000
        for d in store.all_records("documents")
    )
    if used + len(raw) > int(os.environ.get("SALY_MAX_TOTAL_MB", "200")) * 1024 * 1024:
        raise HTTPException(413, "Capacidade configurada do acervo atingida")
    doc = store.save(
        "documents",
        {
            "name": filename,
            "mime": mime,
            "sha256": digest,
            "file_size": len(raw),
            "status": "queued",
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
    job = store.save(
        "document_jobs",
        {"document_id": doc["id"], "status": "queued", "progress": 0, "cancelled": False},
    )
    store.audit("document", "Original privado recebido: " + doc["id"])
    return {"id": doc["id"], "job_id": job["id"], "duplicate": False, "status": "queued"}


def lexical(query, limit=8):
    tokens = re.findall(r"\w+", query, re.UNICODE)[:20]
    if not tokens:
        return []
    with store.db() as c:
        if store.engine.dialect.name == "sqlite":
            q = " OR ".join('"' + t + '"' for t in tokens)
            rows = (
                c.execute(
                    text(
                        "SELECT c.* FROM smolin_fts f JOIN document_chunks c ON c.id=f.id WHERE smolin_fts MATCH :q ORDER BY rank LIMIT :lim"
                    ),
                    {"q": q, "lim": limit},
                )
                .mappings()
                .all()
            )
        else:
            rows = (
                c.execute(
                    text(
                        "SELECT * FROM document_chunks WHERE to_tsvector('portuguese',content) @@ plainto_tsquery('portuguese',:q) LIMIT :lim"
                    ),
                    {"q": query, "lim": limit},
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
                    "url": f"/api/knowledge/{doc['id']}/original#page={r['page']}",
                }
            )
    return results


async def search(query):
    results = lexical(query)
    if embedding_provider.configured and store.setting("preferences", {}).get("privacy", {}).get(
        "remoteConsent", False
    ):
        try:
            vector = (await embedding_provider.encode([query]))[0]
            if store.engine.dialect.name == "postgresql":
                with store.db() as c:
                    rows = (
                        c.execute(
                            select(store.chunks)
                            .where(store.chunks.c.embedding_version == embedding_provider.version)
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
                            select(store.chunks).where(
                                store.chunks.c.embedding_version == embedding_provider.version
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
                if d and d.get("status") in ("ready", "partial", "legacy_text_only"):
                    results.append(
                        {
                            "chunk_id": row["id"],
                            "id": d["id"],
                            "name": d["name"],
                            "page": row["page"],
                            "position": row["position"],
                            "content": row["content"],
                            "source": "smolin",
                            "url": f"/api/knowledge/{d['id']}/original#page={row['page']}",
                        }
                    )
        except (httpx.HTTPError, ValueError, KeyError):
            store.audit(
                "embedding_error", "Busca vetorial indisponível; resultados textuais preservados"
            )
    return results[:8]


def delete_document(key):
    for job in store.all_records("document_jobs"):
        if job["document_id"] == key:
            store.save(
                "document_jobs", {**job, "cancelled": True, "status": "cancelled"}, job["id"]
            )
            task = JOB_TASKS.get(job["id"])
            if task:
                task.get_loop().call_soon_threadsafe(task.cancel)
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
                },
                message["id"],
            )
    store.set_setting("context_epoch", store.setting("context_epoch", 0) + 1)
    for approval in store.all_records("agent_approvals"):
        if approval["status"] == "pending":
            store.save("agent_approvals", {**approval, "status": "expired"}, approval["id"])
    store.audit("document", "Documento, original e índices excluídos: " + key)
