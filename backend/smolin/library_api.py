"""Owner-only incremental library controls, graph and bounded statistical retrieval."""

import asyncio
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import storage as store
from ..security import owner
from . import intelligence, service

router = APIRouter(prefix="/api/knowledge", tags=["smolin-library"])


@router.get("/map")
async def concept_map(q: str = Query("", max_length=300), _=Depends(owner)):
    return await asyncio.to_thread(intelligence.graph, q)


@router.get("/retrieval")
async def retrieval_status(_=Depends(owner)):
    records = intelligence.rows()
    return {
        "local_lsa": os.environ.get("SALY_LOCAL_LSA", "1") == "1",
        "method": intelligence.VERSION,
        "max_chunks": intelligence.MAX_CHUNKS,
        "covered_chunks": min(len(records), intelligence.MAX_CHUNKS),
        "limited": len(records) > intelligence.MAX_CHUNKS,
        "detail": "LSA estatística local treinada no acervo; busca lexical permanece. Não é um modelo neural.",
        "pdf_ocr_available": bool(shutil.which("pdftoppm") and shutil.which("tesseract")),
    }


async def stop_job(key, state):
    job = store.get("document_jobs", key)
    if not job:
        raise HTTPException(404, "Processamento não encontrado")
    if job["status"] not in {"queued", "processing"}:
        raise HTTPException(409, "Só é possível pausar um processamento ativo")
    saved = store.save("document_jobs", {**job, "status": state}, key)
    task = service.JOB_TASKS.get(key)
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    doc = store.get("documents", job["document_id"])
    if doc:
        store.save("documents", {**doc, "status": state}, doc["id"])
    return saved


@router.post("/jobs/{key}/pause")
async def pause(key: str, _=Depends(owner)):
    return await stop_job(key, "paused")


@router.post("/jobs/{key}/resume")
async def resume(key: str, _=Depends(owner)):
    job = store.get("document_jobs", key)
    if not job:
        raise HTTPException(404, "Processamento não encontrado")
    if job["status"] not in {"paused", "failed", "cancelled"}:
        raise HTTPException(409, "Processamento não está pausado, cancelado ou com falha")
    if not store.get("documents", job["document_id"]):
        raise HTTPException(404, "Original já excluído")
    if any(
        j["document_id"] == job["document_id"]
        and j["id"] != key
        and j["status"] in {"queued", "processing", "paused"}
        for j in store.all_records("document_jobs")
    ):
        raise HTTPException(409, "Outro processamento já existe para esse documento")
    job = store.save(
        "document_jobs", {**job, "status": "queued", "cancelled": False, "error": None}, key
    )
    service.start(job["document_id"], key)
    return job


@router.post("/{key}/ocr")
async def pdf_ocr(key: str, _=Depends(owner)):
    doc = store.get("documents", key)
    if not doc or doc.get("kind") != "pdf":
        raise HTTPException(422, "Escolha um documento PDF")
    if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
        raise HTTPException(503, "Instale poppler-utils e tesseract-ocr no servidor para OCR local")
    if any(
        j["document_id"] == key and j["status"] in {"queued", "processing", "paused"}
        for j in store.all_records("document_jobs")
    ):
        raise HTTPException(409, "Documento já tem processamento ativo ou pausado")
    job = store.save(
        "document_jobs",
        {
            "document_id": key,
            "status": "queued",
            "progress": 0,
            "cancelled": False,
            "operation": "ocr",
        },
    )
    service.start(key, job["id"])
    return job
