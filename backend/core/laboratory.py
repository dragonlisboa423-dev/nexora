"""Real local checks and explicit gaps. Never calls a provider or spends API quota."""

import time
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import insert, select

from .. import storage as store
from ..tools import calculate
from .policy import DATA, core_status, load_core, read_bundle
from .quantities import LoadCheck, check_energy_cost, check_load


class CaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    category: str
    input: Any
    expected: Any
    observed: Any
    evidence: str
    status: Literal["passed", "failed", "inconclusive"]
    duration_ms: float
    model_tested: bool = False


def database_roundtrip():
    """Use a real transaction and rollback; no personal record is changed."""
    key = "lab-ephemeral-" + store.uid()
    with store.engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(insert(store.config).values(id=key, data={"probe": key}))
            found = connection.execute(
                select(store.config.c.data).where(store.config.c.id == key)
            ).scalar_one()
            if found != {"probe": key}:
                raise ValueError("Roundtrip divergente")
        finally:
            transaction.rollback()
    with store.db() as connection:
        if connection.execute(select(store.config.c.id).where(store.config.c.id == key)).first():
            raise ValueError("Rollback não confirmado")
    return {"write_read": True, "rollback": True, "database": store.engine.dialect.name}


def _reject_volume_as_mass():
    try:
        LoadCheck.model_validate(
            {"masses": [{"value": 11.4, "unit": "L"}], "capacity": {"value": 12, "unit": "kg"}}
        )
    except ValidationError:
        return {"incompatible_unit_rejected": True}
    raise ValueError("Unidade incompatível aceita")


def _reject_code():
    try:
        calculate("__import__('os')")
    except ValueError:
        return {"code_rejected": True}
    raise ValueError("Código indevido aceito")


def run_local_checks():
    results = []

    def run(key, category, given, expected, operation, matches, evidence):
        start = time.perf_counter()
        try:
            observed = operation()
            status = "passed" if matches(observed) else "failed"
        except Exception:  # noqa: BLE001 - report failure without leaking server configuration
            observed, status = (
                "Verificação não concluída; confira os testes/logs técnicos locais.",
                "failed",
            )
        results.append(
            CaseResult(
                id=key,
                category=category,
                input=given,
                expected=expected,
                observed=observed,
                evidence=evidence,
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 3),
            ).model_dump()
        )

    run(
        "D01",
        "Core",
        "JSON e manifesto locais",
        "SHA-256 e schema compatíveis; 12 regras e 16 casos da semente",
        lambda: {
            "sha256": read_bundle(DATA)[1].sha256,
            "rules": len(read_bundle(DATA)[0].regras_inviolaveis_propostas),
            "cases": len(read_bundle(DATA)[0].avaliacao_e_testes_de_aceitacao.casos),
        },
        lambda r: r["rules"] == 12 and r["cases"] == 16,
        "Leitura e validação locais repetidas nesta execução; checksum não atesta verdade científica.",
    )
    load = {
        "masses": [{"value": v, "unit": "kg"} for v in [11.4, 2, 1.5, 0.8]],
        "capacity": {"value": 12, "unit": "kg"},
    }
    run(
        "D02",
        "Grandezas · caso T01",
        load,
        {"total_kg": 15.7, "excess_kg": 3.7},
        lambda: check_load(load),
        lambda r: r["total_load"]["value"] == 15.7 and r["excess"]["value"] == 3.7,
        "Execução do verificador Decimal; não é resposta gerada nem avaliação do móvel real.",
    )
    energy = {
        "power": {"value": 3, "unit": "W"},
        "hours_per_day": 24,
        "days": 30,
        "tariff_brl_per_kwh": 0.95,
    }
    run(
        "D03",
        "Energia · caso T02",
        energy,
        {"kWh": 2.16, "BRL": 2.052},
        lambda: check_energy_cost(energy),
        lambda r: r["energy"]["value"] == 2.16 and r["cost"]["value"] == 2.052,
        "Execução do verificador Decimal com tarifa informada; não mede consumo real.",
    )
    run(
        "D04",
        "Dimensões",
        "11,4 L como massa em kg",
        "Rejeitar unidade incompatível",
        _reject_volume_as_mass,
        lambda r: r["incompatible_unit_rejected"],
        "Validação real do schema LoadCheck.",
    )
    run(
        "D05",
        "Limites da calculadora",
        "__import__('os')",
        "Rejeitar código",
        _reject_code,
        lambda r: r["code_rejected"],
        "Execução real do parser limitado a aritmética.",
    )
    run(
        "D06",
        "Banco",
        "Registro técnico efêmero e rollback",
        {"write_read": True, "rollback": True},
        database_roundtrip,
        lambda r: r["write_read"] and r["rollback"],
        "Escrita/leitura/rollback no banco atual. Não testa reinício, backup ou armazenamento no Android.",
    )
    return results


def capabilities(provider, embeddings_configured):
    # Only local configuration is inspected. 'Configured' is not 'verified'.
    return [
        {
            "id": "inference",
            "name": "Modelo remoto e agente",
            "state": "configured" if provider.configured else "blocked",
            "detail": "Configuração presente; inferência não foi testada nesta execução."
            if provider.configured
            else "Chave/modelo remoto ausente ou configuração inválida.",
            "last_verification": getattr(provider, "last_probe", None),
        },
        {
            "id": "memory",
            "name": "Memória persistente no servidor",
            "state": "partial",
            "detail": "Banco e edição disponíveis. D06 testa roundtrip; persistência após reinício exige verificação separada. Sem cópia local offline no dispositivo.",
        },
        {
            "id": "smolin",
            "name": "Centro Smolin",
            "state": "configured" if embeddings_configured else "partial",
            "detail": "Upload, extração e busca lexical implementados. Encoder configurado, mas não testado neste laboratório."
            if embeddings_configured
            else "Busca lexical disponível; encoder semântico não configurado. OCR pendente.",
        },
        {
            "id": "voice",
            "name": "Voz própria e áudio",
            "state": "partial",
            "detail": "Vozes/reconhecimento do navegador existentes. Síntese independente e voz feminina própria ainda não implementadas; saída PCM não disponível.",
        },
        {
            "id": "images",
            "name": "Geração e edição de imagens",
            "state": "blocked",
            "detail": "Sem provedor/motor de imagens implementado e conectado. Nenhuma API paga foi habilitada.",
        },
        {
            "id": "videos",
            "name": "Geração e edição de vídeos",
            "state": "blocked",
            "detail": "Sem pipeline de vídeo implementado. Exportação, progresso e cancelamento permanecem pendentes.",
        },
        {
            "id": "android",
            "name": "Android / PWA",
            "state": "partial",
            "detail": "Manifesto, ícones, layout responsivo e cache público existentes. Instalação física e APK Capacitor ainda não verificados.",
        },
        {
            "id": "offline",
            "name": "Dados e IA offline no dispositivo",
            "state": "blocked",
            "detail": "Cache público e página offline existentes. Sem banco local de documentos/memórias nem modelo local conectado; modo avião não permite inferência remota.",
        },
    ]


def run_laboratory(provider, embeddings_configured, app_version):
    start = time.perf_counter()
    core = core_status()
    results = run_local_checks()
    seed, _ = load_core()
    # These are evaluation inputs, not results. Never pass a language test by keyword matching.
    for case in seed.avaliacao_e_testes_de_aceitacao.casos:
        results.append(
            CaseResult(
                id=case.id,
                category="Aceitação do modelo · não executada",
                input=case.entrada,
                expected=case.esperado,
                observed="Não executado: este laboratório local não envia solicitações ao modelo.",
                evidence="Requer avaliação separada com modelo e versão identificados, autorização de quota/custo e revisão de evidências.",
                status="inconclusive",
                duration_ms=0,
            ).model_dump()
        )
    return {
        "kind": "core-lab-v1",
        "timestamp": store.now(),
        "app_version": app_version,
        "rules_version": core["schema_version"],
        "adapter_version": core["adapter_version"],
        "core_sha256": core["sha256"],
        "model_version": provider.model,
        "model_tested": False,
        "provider_requests": 0,
        "mode": "local_deterministic",
        "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        "summary": dict(Counter(r["status"] for r in results)),
        "results": results,
        "capabilities": capabilities(provider, embeddings_configured),
        "scope": "Testes determinísticos e inventário local. Não certifica precisão geral, consciência, AGI, modelo offline ou funcionamento de provedores.",
    }
