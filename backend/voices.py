"""Server speech contracts and an optional real CPU-only eSpeak provider."""

import asyncio
import io
import os
import shutil
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .security import owner, throttle

router = APIRouter(prefix="/api/voices", tags=["speech"])


class SpeechInput(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice_id: str = Field(default="pt-br-f3", pattern=r"^pt-br-f3$")
    rate: float = Field(default=1, ge=0.5, le=2)
    pitch: float = Field(default=1, ge=0.5, le=2)


class SpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, request: SpeechInput) -> bytes:
        """Return verified audio bytes or fail; never synthesize a success response."""


class VoiceCatalogProvider(ABC):
    @abstractmethod
    def catalog(self) -> dict:
        """Report only configured/installed voices, with separate unavailable candidates."""


class EspeakProvider(SpeechProvider, VoiceCatalogProvider):
    def command(self):
        binary = os.environ.get("SALY_ESPEAK_BINARY") or shutil.which("espeak-ng")
        if not binary or not Path(binary).is_file() or not os.access(binary, os.X_OK):
            raise HTTPException(
                503,
                "Motor eSpeak NG não instalado/configurado neste servidor. Escolha uma voz do navegador ou configure o motor local.",
            )
        command = [str(binary)]
        data = os.environ.get("SALY_ESPEAK_DATA_PATH")
        if data:
            if not (Path(data) / "phontab").is_file():
                raise HTTPException(
                    503, "Dados de voz eSpeak não encontrados no caminho configurado."
                )
            command.append("--path=" + data)
        return command

    def environment(self):
        # No API keys/session secrets need to enter the subprocess.
        environment = {"PATH": os.defpath, "LANG": "C.UTF-8"}
        library = os.environ.get("SALY_ESPEAK_LIBRARY_PATH")
        if library:
            environment["LD_LIBRARY_PATH"] = library
        return environment

    def catalog(self):
        try:
            self.command()
            ready, reason = (
                True,
                "Binário configurado; use uma prévia para verificar síntese e reprodução.",
            )
        except HTTPException as error:
            ready, reason = False, error.detail
        return {
            "id": "espeak",
            "name": "eSpeak NG local no servidor",
            "available": ready,
            "status": "nao_testado" if ready else "nao_configurado",
            "detail": reason,
            "license": "GPL-3.0-or-later; componentes auxiliares têm avisos próprios",
            "source": "https://github.com/espeak-ng/espeak-ng",
            "api_cost": 0,
            "voices": [
                {
                    "id": "pt-br-f3",
                    "uri": "saly-espeak:pt-br-f3",
                    "name": "Português BR · variante feminina f3",
                    "language": "pt-BR",
                    "provider": "espeak",
                    "model": "pt-br+f3",
                    "license": "GPL-3.0-or-later",
                    "quality": "Síntese por formantes; voz artificial, não neural. Não é uma voz exclusiva ou natural treinada para a SALY.",
                    "available": ready,
                    "installed": ready,
                    "download_bytes": None,
                    "download_note": "Nenhum modelo é baixado para abrir a interface. O motor/dados são instalação separada no servidor.",
                    "offline_device": False,
                    "offline_server": True,
                    "capabilities": {
                        "pcm": True,
                        "rate": True,
                        "pitch": True,
                        "word_timestamps": False,
                    },
                }
            ],
        }

    async def synthesize(self, request):
        command = self.command() + [
            "-v",
            "pt-br+f3",
            "-s",
            str(round(175 * request.rate)),
            "-p",
            str(min(99, round(50 * request.pitch))),
            "--stdin",
            "--stdout",
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.environment(),
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(request.text.encode("utf-8")), timeout=20
            )
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
            await process.wait()
            raise
        if process.returncode or len(output) > 20 * 1024 * 1024:
            raise HTTPException(
                502,
                "Motor local não produziu áudio utilizável. Confira instalação/dados de voz no servidor.",
            )
        # Streaming stdout may have an unknown RIFF length. Rewrite a complete WAV header.
        try:
            with wave.open(io.BytesIO(output), "rb") as source:
                frames = source.readframes(source.getnframes())
                channels, width, rate = (
                    source.getnchannels(),
                    source.getsampwidth(),
                    source.getframerate(),
                )
            if channels != 1 or width != 2 or rate != 22050 or not frames or not any(frames):
                raise ValueError("Invalid PCM")
            result = io.BytesIO()
            with wave.open(result, "wb") as target:
                target.setparams((channels, width, rate, 0, "NONE", "not compressed"))
                target.writeframes(frames)
            return result.getvalue()
        except (wave.Error, EOFError, ValueError) as error:
            raise HTTPException(502, "Áudio inválido; nenhuma síntese foi confirmada.") from error


provider = EspeakProvider()
gate = asyncio.Semaphore(1)


@router.get("")
def voices(_=Depends(owner)):
    return {
        "providers": [provider.catalog()],
        "candidates": [
            {
                "id": "kokoro",
                "voice": "pf_dora",
                "status": "nao_configurado",
                "detail": "Pesos/compatibilidade e licença do artefato ainda não verificados neste ambiente; consulta oficial bloqueada pela rede. Não instalado.",
            },
            {
                "id": "piper",
                "status": "nao_configurado",
                "detail": "Motor e modelos pt-BR ainda não selecionados/testados com suas licenças. Não instalado.",
            },
        ],
    }


@router.get("/providers/status")
def status(_=Depends(owner)):
    return voices(True)


@router.post("/synthesize")
@router.post("/preview")
async def synthesize(body: SpeechInput, _=Depends(owner)):
    throttle("speech", 12)
    async with gate:
        try:
            audio = await provider.synthesize(body)
        except TimeoutError:
            raise HTTPException(
                504, "Tempo limite da síntese local atingido; nenhuma reprodução foi iniciada."
            ) from None
        except OSError:
            raise HTTPException(
                503, "Motor de voz não pôde iniciar; confira a instalação no servidor."
            ) from None
    return Response(
        audio,
        media_type="audio/wav",
        headers={"X-Saly-Speech-Provider": "espeak", "X-Saly-Voice": "pt-br+f3"},
    )
