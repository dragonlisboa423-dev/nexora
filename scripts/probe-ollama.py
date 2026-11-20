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


async def run(models, path, *, question=ollama.WATER_QUESTION, repeat=2, compare_phi=False):
    store.initialize()
    async with ollama.client() as connection:
        try:
            version = (await connection.get("/api/version", timeout=3)).json()
        except Exception:  # noqa: BLE001 - diagnostics may run while the runtime is offline.
            version = {"version": "unavailable"}
    inventory = await ollama.catalog(include_retired=True)
    report = {
        "models": [],
        "question": question,
        "runtime": version,
        "environment": {
            "hostname": os.uname().nodename,
            "endpoint": ollama.BASE,
            "codespace": os.environ.get("CODESPACE_NAME"),
        },
        "scope": "Geração real pelo Ollama local; não mede latência do navegador/RAG nem verifica exatidão científica.",
    }
    ordered = list(dict.fromkeys(models))
    # Compare first so the last completed run keeps the primary Qwen warm.
    if compare_phi:
        ordered.insert(0, ollama.RETIRED)
    for name in ordered:
        installed = next((item for item in inventory["models"] if item["id"] == name), {})
        if not installed.get("digest"):
            report["models"].append(
                {
                    "model": name,
                    "status": "not_installed",
                    "samples": [],
                    "detail": "Modelo ausente ou servidor indisponível; nenhum download iniciado.",
                }
            )
            save_report(path, report)
            print(json.dumps(report["models"][-1], ensure_ascii=False), flush=True)
            continue
        item = {"model": name, "status": "functional", "samples": []}
        for attempt in range(repeat):
            print(
                f"Testando {name}, execução {attempt + 1}/{repeat}. Primeira carga em CPU pode demorar; Ctrl+C não apaga pesos.",
                flush=True,
            )
            try:
                async with asyncio.timeout(600):
                    result = await ollama.probe(
                        name, question=question, diagnostic_only=name == ollama.RETIRED
                    )
                sample = {"attempt": attempt + 1, "status": "functional", **result}
            except (ProviderError, TimeoutError) as error:
                sample = {
                    "attempt": attempt + 1,
                    "status": "unavailable",
                    "detail": error.detail
                    if isinstance(error, ProviderError)
                    else "Tempo limite do teste excedido.",
                }
                item["status"] = "unavailable"
            item["samples"].append(sample)
            # Keep the old report fields available to readers, plus all timing samples.
            item.update(
                {key: value for key, value in sample.items() if key not in {"attempt", "status"}}
            )
            if item not in report["models"]:
                report["models"].append(item)
            save_report(path, report)
            print(json.dumps({"model": name, **sample}, ensure_ascii=False), flush=True)
            if sample["status"] != "functional":
                break
    required = [item for item in report["models"] if item["model"] in models]
    return 0 if required and all(item["status"] == "functional" for item in required) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Testar e registrar geração local na mesma base da SALY; sem baixar pesos."
    )
    parser.add_argument("models", nargs="*", help="Padrão: qwen2.5:3b")
    parser.add_argument("--report", type=Path, default=ROOT / ".tools/ollama/probe.json")
    parser.add_argument("--question", default=ollama.WATER_QUESTION)
    parser.add_argument("--repeat", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument(
        "--compare-phi",
        action="store_true",
        help="Comparar o Phi já instalado apenas no diagnóstico; não o disponibiliza no chat e nunca baixa seus pesos.",
    )
    args = parser.parse_args()
    models = args.models or [ollama.PRIMARY]
    if any(model not in ollama.MODELS for model in models):
        parser.error("Modelo não permitido")
    try:
        return asyncio.run(
            run(
                models,
                args.report,
                question=args.question,
                repeat=args.repeat,
                compare_phi=args.compare_phi,
            )
        )
    except KeyboardInterrupt:
        print(
            "Teste interrompido. Downloads e verificações já concluídas foram preservados; modelos instalados podem ser testados pelo próprio chat.",
            flush=True,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
