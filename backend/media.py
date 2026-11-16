"""Private media and CPU FFmpeg montage jobs. Distinct from generative video."""

import asyncio
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from pydantic import Field, model_validator
from sqlalchemy import insert, select

from . import storage as store
from .media_providers import image_provider, video_provider
from .personal import Args, normalize_image, remove_asset
from .security import owner, throttle

router = APIRouter(prefix="/api/media", tags=["media"])
TASKS = set()
SEM = asyncio.Semaphore(1)
ACTIVE_PROCESSES = {}
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FORMATS = "mov,matroska,webm,wav,mp3,ogg,flac"
MAX_MEDIA_BYTES = 10 * 1024 * 1024
MAX_OUTPUT_BYTES = 30 * 1024 * 1024


def environment():
    return {"PATH": os.defpath, "LANG": "C.UTF-8"}


def capabilities_data():
    return {
        "image_generation": image_provider.capabilities(),
        "video_generation": video_provider.capabilities(),
        "montage": {
            "available": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
            "engine": "FFmpeg nativo",
            "generation_by_ai": False,
            "max_duration_seconds": 60,
            "max_scenes": 8,
            "max_input_mb": 10,
            "captions_available": FONT.is_file(),
            "remote_services": False,
        },
        "image_editing": {
            "available": True,
            "method": "Pillow local: recorte e rotação; sem edição generativa",
        },
    }


def asset_bytes(key):
    with store.db() as connection:
        content = connection.execute(
            select(store.asset_contents.c.content).where(store.asset_contents.c.id == key)
        ).scalar()
    if content is None:
        raise ValueError("Arquivo privado não encontrado")
    return content


def save_asset(content, mime, **metadata):
    if not content or len(content) > MAX_OUTPUT_BYTES:
        raise ValueError("Arquivo vazio ou acima de 30 MB")
    with store.transaction() as connection:
        store.check_asset_capacity(len(content))
        record = store.save(
            "private_assets",
            {
                "scope": "studio",
                "mime": mime,
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                **metadata,
            },
        )
        connection.execute(insert(store.asset_contents).values(id=record["id"], content=content))
    return record


def probe(path):
    binary = shutil.which("ffprobe")
    if not binary:
        raise ValueError("FFprobe não instalado no servidor")
    command = [
        binary,
        "-v",
        "error",
        "-max_alloc",
        "67108864",
        "-protocol_whitelist",
        "file,pipe",
        "-format_whitelist",
        FORMATS,
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, timeout=15, env=environment(), check=True
        )
        if len(result.stdout) > 100000:
            raise ValueError()
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        streams = data.get("streams", [])
        if not 0 < duration <= 61 or len(streams) > 8:
            raise ValueError()
        if any(s.get("width", 0) > 3840 or s.get("height", 0) > 2160 for s in streams):
            raise ValueError()
        return {"duration": duration, "streams": streams}
    except (subprocess.SubprocessError, KeyError, ValueError, TypeError):
        raise ValueError("Mídia inválida, acima de 60 s ou dimensões incompatíveis") from None


def ffmpeg_base():
    binary = shutil.which("ffmpeg")
    if not binary:
        raise ValueError("FFmpeg não instalado no servidor")
    return [
        binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-max_alloc",
        "67108864",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-filter_complex_threads",
        "1",
    ]


def ffmpeg_input(path):
    return ["-protocol_whitelist", "file,pipe", "-format_whitelist", FORMATS, "-i", str(path)]


def normalize_av(raw, kind):
    with tempfile.TemporaryDirectory(prefix="saly-av-") as directory:
        source = Path(directory) / "input.bin"
        source.write_bytes(raw)
        info = probe(source)
        has_video = any(s.get("codec_type") == "video" for s in info["streams"])
        has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
        if (kind == "video" and not has_video) or (
            kind == "audio" and (not has_audio or has_video)
        ):
            raise ValueError("Tipo de mídia não corresponde ao conteúdo")
        output = Path(directory) / ("output.mp4" if kind == "video" else "output.wav")
        command = ffmpeg_base() + ffmpeg_input(source) + ["-t", "60", "-map_metadata", "-1"]
        if kind == "video":
            command += [
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "24",
                "-c:a",
                "aac",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
            ]
        else:
            command += ["-map", "0:a:0", "-vn", "-c:a", "pcm_s16le", "-ac", "1", "-ar", "22050"]
        command += ["-fs", str(MAX_OUTPUT_BYTES), str(output)]
        try:
            subprocess.run(command, capture_output=True, timeout=90, check=True, env=environment())
        except subprocess.SubprocessError:
            raise ValueError("Falha ao decodificar/normalizar mídia") from None
        checked = probe(output)
        if abs(checked["duration"] - info["duration"]) > 1.0:
            raise ValueError("Mídia normalizada ficou incompleta")
        return output.read_bytes(), checked


@router.get("/capabilities")
def capabilities(_=Depends(owner)):
    return capabilities_data()


@router.get("/assets")
def assets(_=Depends(owner)):
    return [
        a
        for a in store.all_records("private_assets")
        if a.get("scope") == "studio" and not a.get("book_id")
    ]


@router.post("/assets")
def upload(
    kind: Literal["image", "audio", "video"],
    book_id: str | None = None,
    file: UploadFile = File(...),
    _=Depends(owner),
):
    throttle("media-upload", 20)
    if book_id and not store.get("books", book_id):
        raise HTTPException(404, "Livro não encontrado")
    raw = file.file.read(MAX_MEDIA_BYTES + 1)
    if len(raw) > MAX_MEDIA_BYTES:
        raise HTTPException(413, "Arquivo acima de 10 MB")
    try:
        if kind == "image":
            content = normalize_image(raw)
            mime = "image/png"
            metadata = {}
        else:
            content, info = normalize_av(raw, kind)
            mime = "video/mp4" if kind == "video" else "audio/wav"
            metadata = {"duration": info["duration"]}
        return save_asset(content, mime, kind=kind, book_id=book_id, role="input", **metadata)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.delete("/assets/{key}")
def delete_asset(key: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão do arquivo")
    with store.transaction():
        asset = store.get("private_assets", key)
        if not asset or asset.get("scope") != "studio" or asset.get("book_id"):
            raise HTTPException(404, "Arquivo não encontrado")
        for job in store.all_records("media_jobs"):
            if key in job.get("input_asset_ids", []) and job["status"] in {
                "queued",
                "running",
                "cancel_requested",
            }:
                raise HTTPException(409, "Arquivo em uso por tarefa ativa")
        remove_asset(key)
    return {"deleted": True}


class ImageEdit(Args):
    asset_id: str
    rotate: Literal[0, 90, 180, 270] = 0
    crop: tuple[int, int, int, int] | None = None
    confirm: bool = False


@router.post("/images/edit")
def edit_image(body: ImageEdit, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a edição local")
    record = store.get("private_assets", body.asset_id)
    if not record or record.get("scope") != "studio" or record.get("mime") != "image/png":
        raise HTTPException(422, "Escolha uma imagem do Estúdio")
    with Image.open(io.BytesIO(asset_bytes(body.asset_id))) as image:
        if body.crop:
            x0, y0, x1, y1 = body.crop
            if not 0 <= x0 < x1 <= image.width or not 0 <= y0 < y1 <= image.height:
                raise HTTPException(422, "Recorte fora da imagem")
            image = image.crop(body.crop)
        image = image.rotate(-body.rotate, expand=True)
        image.info.clear()
        output = io.BytesIO()
        image.save(output, format="PNG")
    return save_asset(
        output.getvalue(),
        "image/png",
        kind="image",
        role="edited",
        parent_asset_id=body.asset_id,
        method="local_crop_rotate",
    )


class Scene(Args):
    asset_id: str
    duration: float = Field(default=3, ge=0.5, le=15)
    trim_start: float = Field(default=0, ge=0, le=59)
    caption: str = Field(default="", max_length=300)


class Montage(Args):
    scenes: list[Scene] = Field(min_length=1, max_length=8)
    orientation: Literal["landscape", "portrait"] = "landscape"
    transition: Literal["cut", "fade"] = "cut"
    narration_asset_id: str | None = None
    music_asset_id: str | None = None
    confirm: bool = False

    @model_validator(mode="after")
    def duration_limit(self):
        if sum(s.duration for s in self.scenes) > 60:
            raise ValueError("Montagem acima de 60 segundos")
        return self


class GenerateImage(Args):
    prompt: str = Field(min_length=1, max_length=2048)
    steps: int = Field(default=4, ge=1, le=8)
    confirm: bool = False


def new_job(kind, arguments, input_ids, provider):
    with store.transaction():
        active = [
            j
            for j in store.all_records("media_jobs")
            if j["status"] in {"queued", "running", "cancel_requested"}
        ]
        if len(active) >= 3:
            raise HTTPException(429, "Aguarde as tarefas atuais; fila limitada a três")
        return store.save(
            "media_jobs",
            {
                "kind": kind,
                "provider": provider,
                "arguments": arguments,
                "input_asset_ids": input_ids,
                "output_asset_ids": [],
                "status": "queued",
                "progress": None,
                "error": None,
            },
        )


@router.post("/montage")
async def montage(body: Montage, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme a exportação local")
    if not capabilities_data()["montage"]["available"]:
        raise HTTPException(503, "Instale FFmpeg e FFprobe no servidor")
    ids = []
    for scene in body.scenes:
        asset = store.get("private_assets", scene.asset_id)
        if (
            not asset
            or asset.get("book_id")
            or asset.get("scope") != "studio"
            or asset.get("kind") not in {"image", "video"}
        ):
            raise HTTPException(422, "Cena requer imagem ou clipe privado do Estúdio")
        if asset["kind"] == "video" and scene.trim_start + scene.duration > asset["duration"] + 0.1:
            raise HTTPException(422, "Corte ultrapassa duração do clipe")
        if scene.caption and not FONT.is_file():
            raise HTTPException(503, "Fonte local para legenda indisponível")
        ids.append(scene.asset_id)
    for key in (body.narration_asset_id, body.music_asset_id):
        if not key:
            continue
        asset = store.get("private_assets", key)
        if (
            not asset
            or asset.get("scope") != "studio"
            or asset.get("kind") != "audio"
            or asset.get("book_id")
        ):
            raise HTTPException(422, "Trilha requer áudio privado do Estúdio")
        ids.append(key)
    job = new_job("montage", body.model_dump(exclude={"confirm"}), ids, "ffmpeg_local")
    start(job["id"])
    return job


@router.post("/images/generate")
async def generate(body: GenerateImage, _=Depends(owner)):
    if not body.confirm:
        raise HTTPException(400, "Confirme o envio do prompt ao provedor gratuito declarado")
    if not image_provider.capabilities()["configured"]:
        raise HTTPException(
            503,
            "Provedor de imagens não configurado; conta Free, credencial e termos precisam de revisão privada",
        )
    job = new_job("image_generation", body.model_dump(exclude={"confirm"}), [], "cloudflare")
    start(job["id"])
    return job


@router.post("/videos/generate")
def generate_video(_=Depends(owner)):
    raise HTTPException(
        503, "Geração de vídeo por IA não configurada. Use montagem local identificada como edição."
    )


@router.get("/jobs")
def jobs(_=Depends(owner)):
    return store.all_records("media_jobs")


@router.post("/jobs/{key}/cancel")
def cancel(key: str, _=Depends(owner)):
    with store.transaction():
        job = store.get("media_jobs", key)
        if not job:
            raise HTTPException(404, "Tarefa não encontrada")
        if job["status"] not in {"queued", "running", "cancel_requested"}:
            raise HTTPException(409, "Tarefa já encerrada")
        return store.save(
            "media_jobs",
            {
                **job,
                "status": "cancelled" if job["status"] == "queued" else "cancel_requested",
                "cancellation_scope": "local; provedor remoto pode já ter consumido cota",
            },
            key,
        )


@router.delete("/jobs/{key}")
def delete_job(key: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme excluir histórico e resultados desta tarefa")
    with store.transaction():
        job = store.get("media_jobs", key)
        if not job:
            raise HTTPException(404, "Tarefa não encontrada")
        if job["status"] in {"queued", "running", "cancel_requested"}:
            raise HTTPException(409, "Cancele e aguarde encerrar a tarefa")
        for asset_id in job.get("output_asset_ids", []):
            if store.get("private_assets", asset_id):
                remove_asset(asset_id)
        store.remove("media_jobs", key)
    return {"deleted": True}


def start(key):
    task = asyncio.create_task(process(key))
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)


def cancelled(key):
    job = store.get("media_jobs", key)
    return not job or job["status"] in {"cancel_requested", "cancelled"}


async def run_ffmpeg(command, key, duration, stage):
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=environment(),
        start_new_session=True,
    )
    ACTIVE_PROCESSES[key] = process
    try:
        async with asyncio.timeout(180):
            while True:
                line = await process.stdout.readline()
                if cancelled(key):
                    raise asyncio.CancelledError()
                if not line:
                    break
                if line.startswith(b"out_time_us="):
                    try:
                        seconds = max(0, int(line.split(b"=")[1]) / 1e6)
                    except ValueError:
                        continue
                    with store.transaction():
                        job = store.get("media_jobs", key)
                        if job and job["status"] == "running":
                            store.save(
                                "media_jobs",
                                {
                                    **job,
                                    "progress": {
                                        "stage": stage,
                                        "encoded_seconds": seconds,
                                        "target_seconds": duration,
                                        "percent": round(min(100, seconds / duration * 100), 1),
                                    },
                                },
                                key,
                            )
            if await process.wait() != 0:
                raise ValueError("FFmpeg não concluiu a etapa de exportação")
    finally:
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
        ACTIVE_PROCESSES.pop(key, None)


async def render(arguments, key):
    total = sum(s["duration"] for s in arguments["scenes"])
    width, height = (640, 360) if arguments["orientation"] == "landscape" else (360, 640)
    with tempfile.TemporaryDirectory(prefix="saly-render-") as directory:
        root = Path(directory)
        clips = []
        for index, scene in enumerate(arguments["scenes"]):
            if cancelled(key):
                raise asyncio.CancelledError()
            asset = store.get("private_assets", scene["asset_id"])
            if not asset:
                raise ValueError("Arquivo de entrada removido")
            is_image = asset["kind"] == "image"
            source = root / f"input-{index}.{'png' if is_image else 'mp4'}"
            source.write_bytes(asset_bytes(asset["id"]))
            clip = root / f"scene-{index}.mp4"
            command = ffmpeg_base()
            if is_image:
                command += ["-loop", "1", "-i", str(source)]
            else:
                command += ["-ss", str(scene["trim_start"])] + ffmpeg_input(source)
            filters = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=24"
            if arguments["transition"] == "fade":
                filters += f",fade=t=in:st=0:d=0.25,fade=t=out:st={max(0, scene['duration'] - 0.25)}:d=0.25"
            if scene["caption"]:
                caption = root / f"caption-{index}.txt"
                caption.write_text(scene["caption"], encoding="utf-8")
                filters += f",drawtext=fontfile={FONT}:textfile={caption}:expansion=none:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.65:x=(w-text_w)/2:y=h-text_h-22"

            command += [
                "-t",
                str(scene["duration"]),
                "-an",
                "-vf",
                filters,
                "-map_metadata",
                "-1",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-fs",
                str(MAX_OUTPUT_BYTES),
                "-progress",
                "pipe:1",
                "-nostats",
                str(clip),
            ]
            await run_ffmpeg(
                command, key, scene["duration"], f"Cena {index + 1}/{len(arguments['scenes'])}"
            )
            clips.append(clip.name)
        concat = root / "scenes.txt"
        concat.write_text("".join("file '" + name + "'\n" for name in clips))
        output = root / "export.mp4"
        command = ffmpeg_base() + [
            "-f",
            "concat",
            "-safe",
            "1",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(concat),
        ]
        tracks = []
        for name in ("narration_asset_id", "music_asset_id"):
            if arguments.get(name):
                track = root / f"{name}.wav"
                track.write_bytes(asset_bytes(arguments[name]))
                tracks.append(name)
                command += ["-stream_loop", "-1"] + ffmpeg_input(track)
        if len(tracks) == 2:
            command += [
                "-filter_complex",
                "[1:a]volume=1[a1];[2:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=longest[a]",
                "-map",
                "0:v:0",
                "-map",
                "[a]",
            ]
        elif tracks:
            command += ["-map", "0:v:0", "-map", "1:a:0"]
        else:
            command += ["-map", "0:v:0", "-an"]
        command += [
            "-t",
            str(total),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ac",
            "2",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            "-fs",
            str(MAX_OUTPUT_BYTES),
            "-progress",
            "pipe:1",
            "-nostats",
            str(output),
        ]
        await run_ffmpeg(command, key, total, "Montagem e trilhas")
        info = await asyncio.to_thread(probe, output)
        video = [s for s in info["streams"] if s.get("codec_type") == "video"]
        if (
            not video
            or video[0].get("width") != width
            or video[0].get("height") != height
            or abs(info["duration"] - total) > 0.5
        ):
            raise ValueError("Exportação incompleta ou dimensões inválidas")
        return output.read_bytes(), {
            "duration": info["duration"],
            "width": width,
            "height": height,
            "validated_by": "ffprobe + decodificação/encodificação FFmpeg",
        }


async def process(key):
    async with SEM:
        with store.transaction():
            job = store.get("media_jobs", key)
            if not job or job["status"] != "queued":
                return
            job = store.save(
                "media_jobs", {**job, "status": "running", "started_at": store.now()}, key
            )
        try:
            if job["kind"] == "montage":
                content, info = await render(job["arguments"], key)
                mime = "video/mp4"
                kind = "video"
            else:
                raw = await image_provider.generate(**job["arguments"])
                content = await asyncio.to_thread(normalize_image, raw)
                info = {"validated_by": "Pillow decode + PNG normalization"}
                mime = "image/png"
                kind = "image"
            with store.transaction():
                current = store.get("media_jobs", key)
                if current["status"] == "cancel_requested":
                    raise asyncio.CancelledError()
                asset = save_asset(content, mime, kind=kind, role="output", job_id=key, **info)
                store.save(
                    "media_jobs",
                    {
                        **current,
                        "status": "completed",
                        "output_asset_ids": [asset["id"]],
                        "finished_at": store.now(),
                        "result_sha256": asset["sha256"],
                    },
                    key,
                )
        except asyncio.CancelledError:
            with store.transaction():
                current = store.get("media_jobs", key)
                if current:
                    store.save(
                        "media_jobs",
                        {**current, "status": "cancelled", "finished_at": store.now()},
                        key,
                    )
        except Exception as error:  # noqa: BLE001 - persist failure of every background job without logging private input
            with store.transaction():
                current = store.get("media_jobs", key)
                if current:
                    store.save(
                        "media_jobs",
                        {
                            **current,
                            "status": "cancelled"
                            if current["status"] == "cancel_requested"
                            else "failed",
                            "error_code": type(error).__name__,
                            "error": "Não foi possível validar/exportar a mídia. Confira arquivo, configuração, cota e disponibilidade do motor; nenhuma alternativa paga foi usada.",
                            "finished_at": store.now(),
                        },
                        key,
                    )


def recover_jobs():
    for job in store.all_records("media_jobs"):
        if job["status"] == "queued":
            start(job["id"])
        elif job["status"] in {"running", "cancel_requested"}:
            store.save(
                "media_jobs",
                {
                    **job,
                    "status": "cancelled" if job["status"] == "cancel_requested" else "failed",
                    "error": "Processo interrompido pelo reinício; sem repetir requisição remota automaticamente.",
                    "finished_at": store.now(),
                },
                job["id"],
            )


async def shutdown():
    for task in tuple(TASKS):
        task.cancel()
    if TASKS:
        await asyncio.gather(*tuple(TASKS), return_exceptions=True)
