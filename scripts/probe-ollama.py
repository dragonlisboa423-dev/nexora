"""Actual local generation; persist the same digest-bound readiness used by the app."""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Match the working directory used by start.sh/setup-ollama.sh for relative DB paths.
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from backend import storage as store
from backend.llm import ollama
from backend.llm.provider import ProviderError


def save_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="probe-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(report, output, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


async def run(models, path):
    store.initialize()
    report = {"models": [], "scope": "Geração textual real; não verifica ferramentas/visão."}
    for name in dict.fromkeys(models):
        print(
            f"Testando geração local de {name}; primeira carga em CPU pode demorar. Ctrl+C interrompe o teste, sem apagar pesos.",
            flush=True,
        )
        try:
            async with asyncio.timeout(240):
                result = await ollama.probe(name)
            item = {"model": name, "status": "functional", **result}
        except (ProviderError, TimeoutError) as error:
            item = {
                "model": name,
                "status": "unavailable",
                "detail": error.detail
                if isinstance(error, ProviderError)
                else "Tempo limite de teste excedido; tente uma mensagem na SALY.",
            }
        report["models"].append(item)
        save_report(path, report)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    return 0 if all(item["status"] == "functional" for item in report["models"]) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Testar e registrar geração local na mesma base da SALY; sem baixar pesos."
    )
    parser.add_argument("models", nargs="*", help="Padrão: granite4:3b e phi4-mini")
    parser.add_argument("--report", type=Path, default=ROOT / ".tools/ollama/probe.json")
    args = parser.parse_args()
    models = args.models or ["granite4:3b", "phi4-mini"]
    if any(model not in ollama.MODELS for model in models):
        parser.error("Modelo não permitido")
    try:
        return asyncio.run(run(models, args.report))
    except KeyboardInterrupt:
        print(
            "Teste interrompido. Downloads e verificações já concluídas foram preservados; modelos instalados podem ser testados pelo próprio chat.",
            flush=True,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
