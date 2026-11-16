"""Bounded local OCR and AV inspection. Metadata is never described as semantic understanding."""

import json
import math
import os
import shutil
import subprocess
import warnings
from pathlib import Path

from PIL import Image, ImageOps

ENV = {"PATH": os.defpath, "LANG": "C.UTF-8", "OMP_THREAD_LIMIT": "1"}
FORMATS = "mov,matroska,webm,wav,mp3,ogg,flac,aac"
Image.MAX_IMAGE_PIXELS = 16_000_000


def inspect_media(path):
    binary = shutil.which("ffprobe")
    if not binary:
        raise ValueError("FFmpeg/FFprobe não instalado")
    response = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-max_alloc",
            "67108864",
            "-protocol_whitelist",
            "file,pipe",
            "-format_whitelist",
            FORMATS,
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        timeout=20,
        env=ENV,
        check=True,
    )
    if len(response.stdout) > 100000:
        raise ValueError("Metadados acima do limite")
    info = json.loads(response.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or not 0 < duration <= 7200:
        raise ValueError("Duração inválida ou acima de duas horas")
    if any(s.get("width", 0) > 7680 or s.get("height", 0) > 4320 for s in info.get("streams", [])):
        raise ValueError("Dimensões acima do limite")
    return {"duration_seconds": duration, "streams": info.get("streams", [])}


def ocr(path, folder, identifier="image"):
    if not shutil.which("tesseract"):
        return "", "OCR não instalado neste servidor."
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            image.load()
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            normalized.thumbnail((2400, 2400))
            normalized.info.clear()
            output = Path(folder) / (identifier + ".png")
            normalized.save(output)
    languages = (
        subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, timeout=5, env=ENV, check=True
        )
        .stdout.decode()
        .splitlines()[1:]
    )
    language = (
        "por+eng"
        if "por" in languages and "eng" in languages
        else "por"
        if "por" in languages
        else "eng"
        if "eng" in languages
        else None
    )
    if not language:
        return "", "OCR sem idioma português/inglês instalado."
    result = subprocess.run(
        ["tesseract", str(output), "stdout", "-l", language, "--psm", "3"],
        capture_output=True,
        timeout=30,
        env=ENV,
        check=True,
    )
    text = result.stdout.decode("utf-8", errors="replace")[:200000].strip()
    return text, "OCR local " + language + "; pode conter erros. Não é descrição visual completa."


def extract_media(path, kind, folder):
    info = inspect_media(path)
    if kind == "audio":
        return {
            "pages": [],
            "title": "",
            "author": "",
            "unit": "segment",
            "media_info": info,
            "status": "transcription_required",
            "notice": "Áudio preservado e metadados verificados. A fala exige transcrição local configurada ou ação remota explicitamente autorizada.",
        }
    if not shutil.which("ffmpeg"):
        raise ValueError("FFmpeg não instalado")
    duration = info["duration_seconds"]
    pages = []
    notes = []
    # Samples are explicitly bounded and timestamped, not a claim to inspect every video frame.
    for index in range(6):
        stamp = (duration - 0.05) * index / 6
        frame = Path(folder) / f"frame-{index}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-filter_threads",
                "1",
                "-ss",
                str(stamp),
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                FORMATS,
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease",
                "-y",
                str(frame),
            ],
            capture_output=True,
            timeout=25,
            env=ENV,
            check=True,
        )
        if not frame.is_file():
            continue
        text, note = ocr(frame, folder, f"ocr-{index}")
        notes.append(note)
        pages.append(
            {
                "page": index + 1,
                "content": text,
                "start_seconds": round(stamp, 3),
                "end_seconds": round(stamp, 3),
                "label": f"Quadro amostrado em {stamp:.2f}s",
                "method": "sampled_frame_ocr",
            }
        )
    return {
        "pages": pages,
        "title": "",
        "author": "",
        "unit": "frame",
        "media_info": info,
        "status": "partial" if any(p["content"] for p in pages) else "transcription_required",
        "notice": "Foram amostrados até seis quadros para OCR; não é análise completa de cenas, movimentos ou da fala. "
        + (notes[0] if notes else "")
        + " O áudio exige transcrição separada.",
    }


def wav_for_transcription(path, folder):
    info = inspect_media(path)
    if not any(s.get("codec_type") == "audio" for s in info["streams"]):
        raise ValueError("Arquivo sem faixa de áudio")
    if info["duration_seconds"] > 1800:
        raise ValueError("Transcrição local limitada a 30 minutos por arquivo")
    target = Path(folder) / "speech.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-threads",
            "1",
            "-protocol_whitelist",
            "file,pipe",
            "-format_whitelist",
            FORMATS,
            "-i",
            str(path),
            "-vn",
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-map_metadata",
            "-1",
            "-y",
            str(target),
        ],
        capture_output=True,
        timeout=90,
        env=ENV,
        check=True,
    )
    return target, info
