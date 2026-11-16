"""Opt-in functional probes of local engines. Never sends provider requests."""

import asyncio
import hashlib
import inspect
import io
import shutil
import subprocess
import tempfile
import time
import wave
from collections import Counter
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter

from . import storage as store
from .biology import initial_book
from .core.laboratory import CaseResult, capabilities
from .core.policy import core_status
from .library import Book
from .media import environment, ffmpeg_base, probe
from .personal import Link, Purchase, normalize
from .timeutils import instant, next_occurrence
from .voices import SpeechInput
from .voices import provider as voice


def calendar_probe():
    start = instant("2026-01-31T10:00", "America/Sao_Paulo")
    following = next_occurrence(start, "America/Sao_Paulo", "FREQ=MONTHLY", start)
    try:
        instant("2026-03-08T02:30", "America/New_York")
    except ValueError:
        gap = True
    else:
        gap = False
    if following.month != 3 or following.day != 31 or not gap:
        raise ValueError("Divergência de calendário")
    return {
        "monthly_next": following.isoformat(),
        "dst_gap_rejected": gap,
        "scheduler": "Inspecionado separadamente; teste não dispara alarmes pessoais",
    }


def money_probe():
    data = normalize(
        "purchases",
        {
            "product": "Probe local",
            "price_cents": 12345,
            "quantity": 2,
            "shipping_cents": 999,
            "discount_cents": 100,
            "purchased_on": "2026-11-16",
        },
    )
    try:
        Purchase.model_validate({"product": "x", "price_cents": 1.2})
    except ValidationError:
        rejected = True
    else:
        rejected = False
    if data["total_cents"] != 25589 or not rejected:
        raise ValueError("Cálculo monetário divergente")
    return {"total_cents": data["total_cents"], "float_rejected": rejected, "records_written": 0}


def url_probe():
    try:
        Link.model_validate({"title": "probe", "url": "javascript:alert(1)", "drawer_id": "probe"})
    except ValidationError:
        return {"executable_scheme_rejected": True, "external_requests": 0}
    raise ValueError("Esquema não rejeitado")


def book_probe():
    book = Book.model_validate(initial_book())
    return {
        "chapters": len(book.chapters),
        "pages": sum(len(c.pages) for c in book.chapters),
        "publication_status": book.publication_status,
        "code_execution": False,
        "scientific_review": "Pendente; validação de schema não certifica conteúdo",
    }


def image_probe():
    source = Image.new("RGB", (80, 50), "green")
    edited = source.crop((10, 5, 60, 40)).rotate(90, expand=True)
    output = io.BytesIO()
    edited.save(output, format="PNG")
    decoded = Image.open(io.BytesIO(output.getvalue()))
    decoded.load()
    if decoded.size != (35, 50):
        raise ValueError("Edição divergente")
    return {
        "dimensions": list(decoded.size),
        "sha256": hashlib.sha256(output.getvalue()).hexdigest(),
        "provider_requests": 0,
    }


def pdf_probe():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    raw = io.BytesIO()
    writer.write(raw)
    parsed = PdfReader(io.BytesIO(raw.getvalue()))
    if len(parsed.pages) != 1:
        raise ValueError("PDF divergente")
    return {
        "pages": 1,
        "parser": "pypdf",
        "original_private_document_read": False,
        "ocr_tested": False,
        "semantic_encoder_tested": False,
    }


def video_probe():
    with tempfile.TemporaryDirectory(prefix="saly-lab-video-") as directory:
        output = Path(directory) / "probe.mp4"
        command = ffmpeg_base() + [
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:d=0.5",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
        subprocess.run(command, env=environment(), capture_output=True, timeout=20, check=True)
        info = probe(output)
        return {
            "duration": info["duration"],
            "bytes": output.stat().st_size,
            "engine": "FFmpeg + FFprobe",
            "scope": "Codec local; não geração por IA, nem teste completo da montagem",
        }


async def speech_probe():
    raw = await voice.synthesize(SpeechInput(text="Verificação local da voz da Saly."))
    with wave.open(io.BytesIO(raw), "rb") as result:
        if result.getnframes() == 0:
            raise ValueError("PCM vazio")
        return {
            "pcm_frames": result.getnframes(),
            "rate": result.getframerate(),
            "channels": result.getnchannels(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "natural_neural_voice": False,
            "physical_playback_tested": False,
        }


async def run_feature_checks(provider, embeddings_configured, app_version):
    start = time.perf_counter()
    results = []

    async def run(key, category, operation, expected, evidence):
        began = time.perf_counter()
        try:
            observed = operation()
            if inspect.isawaitable(observed):
                observed = await observed
            status = "passed"
        except HTTPException as error:
            observed = (
                "Dependência local indisponível ou incompatível; consulte configuração do recurso."
            )
            status = "inconclusive" if error.status_code == 503 else "failed"
        except (ValueError, OSError, subprocess.SubprocessError, TimeoutError):
            observed = "Verificação local falhou; consulte instalação e testes técnicos."
            status = "failed"
        results.append(
            CaseResult(
                id=key,
                category=category,
                input="Probe técnico fixo, sem conteúdo pessoal",
                expected=expected,
                observed=observed,
                evidence=evidence,
                status=status,
                duration_ms=round((time.perf_counter() - began) * 1000, 3),
            ).model_dump()
        )

    await run(
        "F01",
        "Agenda · datas/recorrência",
        calendar_probe,
        "Pular fevereiro sem dia 31; rejeitar horário inexistente",
        "Executa funções reais. Não testa entrega nativa nem cria alarmes.",
    )
    await run(
        "F02",
        "Compras · centavos",
        money_probe,
        25589,
        "Cálculo e validação reais; sem alterar dados financeiros.",
    )
    await run(
        "F03",
        "Espaço · segurança de URL",
        url_probe,
        "Rejeitar javascript:",
        "Validação real sem visitar o destino.",
    )
    await run(
        "F04",
        "Biblioteca · esquema editorial",
        book_probe,
        "Rascunho original com oito capítulos/nove páginas",
        "Valida o conteúdo distribuído; revisão científica permanece pendente.",
    )
    await run(
        "F05",
        "Imagens · edição local",
        image_probe,
        [35, 50],
        "PNG real criado, editado e decodificado; removido ao fim da execução.",
    )
    await run(
        "F06",
        "Smolin · parser PDF",
        pdf_probe,
        "Abrir PDF sintético de uma página",
        "Não lê seus documentos e não certifica OCR ou embeddings.",
    )
    await run(
        "F07",
        "Voz · WAV real",
        speech_probe,
        "PCM real ou dependência explicitamente pendente",
        "Síntese local; não verifica alto-falante físico nem naturalidade.",
    )
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        await run(
            "F08",
            "Vídeo · codec local",
            lambda: asyncio.to_thread(video_probe),
            "MP4 real de meio segundo",
            "Encode e probe reais em diretório temporário, sem arquivos pessoais.",
        )
    else:
        results.append(
            CaseResult(
                id="F08",
                category="Vídeo · codec local",
                input="FFmpeg/FFprobe",
                expected="Ferramentas locais disponíveis",
                observed="Ferramenta ausente; instale o motor para testar.",
                evidence="Nenhum arquivo falso produzido.",
                status="inconclusive",
                duration_ms=0,
            ).model_dump()
        )
    core = core_status()
    return {
        "kind": "feature-lab-v1",
        "timestamp": store.now(),
        "app_version": app_version,
        "rules_version": core["schema_version"],
        "core_sha256": core["sha256"],
        "model_version": provider.model,
        "model_tested": False,
        "provider_requests": 0,
        "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        "summary": dict(Counter(r["status"] for r in results)),
        "results": results,
        "capabilities": capabilities(provider, embeddings_configured),
        "scope": "Probes locais fixos, sem APIs externas. Não certificam entrega de notificações, instalação Android, armazenamento deste aparelho, geração remota, correção científica geral ou a suíte completa.",
    }
