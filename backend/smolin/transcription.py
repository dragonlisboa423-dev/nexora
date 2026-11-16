"""Local-only speech transcription. Never contacts Groq or downloads a model implicitly."""

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

MODEL_SHA = "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9"
MODEL_URL = "https://openaipublic.azureedge.net/main/whisper/models/" + MODEL_SHA + "/tiny.pt"


def model_path():
    return Path(
        os.environ.get("SALY_SMOLIN_WHISPER_MODEL_PATH")
        or str(Path(__file__).resolve().parents[2] / ".tools/whisper/tiny.pt")
    ).resolve()


def capability():
    dependencies = bool(importlib.util.find_spec("whisper") and importlib.util.find_spec("torch"))
    installed = model_path().is_file()
    return {
        "provider": "Whisper tiny local em CPU",
        "available": dependencies and installed,
        "dependencies_installed": dependencies,
        "model_installed": installed,
        "model": "tiny multilíngue",
        "api_cost": 0,
        "max_duration_seconds": 1800,
        "scope": "Transcreve a fala; não certifica exatidão nem compreensão completa de cenas. Nenhum modelo é baixado ao enviar um arquivo.",
        "setup": "bash scripts/install-transcription.sh",
    }


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (580, 580))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    try:
        path = model_path()
        with path.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != MODEL_SHA:
                raise ValueError("Hash do modelo divergente")
        import torch
        import whisper

        from .media_text import wav_for_transcription

        torch.set_num_threads(2)
        wav, info = wav_for_transcription(sys.argv[1], Path(sys.argv[1]).parent)
        model = whisper.load_model(str(path), device="cpu")
        result = model.transcribe(str(wav), fp16=False, verbose=None)
        pages = [
            {
                "page": i + 1,
                "content": segment["text"].strip(),
                "start_seconds": round(segment["start"], 3),
                "end_seconds": round(segment["end"], 3),
                "method": "whisper_local",
            }
            for i, segment in enumerate(result["segments"])
            if segment["text"].strip()
        ]
        if sum(len(p["content"]) for p in pages) > 2_000_000:
            raise ValueError("Transcrição extensa demais")
        print(
            json.dumps(
                {
                    "pages": pages,
                    "title": "",
                    "author": "",
                    "unit": "segment",
                    "media_info": info,
                    "status": "partial" if pages else "stored_only",
                    "notice": "Transcrição automática local Whisper tiny; revise possíveis erros. Não é compreensão completa de cenas.",
                    "transcribed": True,
                },
                ensure_ascii=False,
            )
        )
    except Exception:  # noqa: BLE001 - never echo paths or model/input content on failure
        print(
            json.dumps(
                {
                    "error": "Transcrição local não concluída; verifique dependências, hash do modelo, faixa de áudio e limite de 30 minutos."
                }
            )
        )
        raise SystemExit(1)
