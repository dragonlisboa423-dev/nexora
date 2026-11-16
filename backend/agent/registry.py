import asyncio
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update

from .. import storage as store
from ..core.quantities import EnergyCheck, LoadCheck, check_energy_cost, check_load
from ..integrations import integrations
from ..memory import index_memory, search_memories
from ..planning import (
    Alarm,
    CalendarEvent,
    delete_alarm,
    delete_event,
    normalized_alarm,
    normalized_event,
    save_alarm,
    save_event,
)
from ..services import Memory, memory_delete, memory_save
from ..smolin.service import search as smolin_search
from ..tools import calculate
from ..voices import voices as voice_catalog


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Query(Args):
    query: str = Field(min_length=1, max_length=500)


class Empty(Args):
    pass


class Key(Args):
    id: str = Field(min_length=1, max_length=64)


class Excerpt(Args):
    chunk_id: str = Field(min_length=1, max_length=64)


class SaveMemory(Args):
    content: str = Field(min_length=1, max_length=20000)
    category: str = "informacoes"


class UpdateMemory(SaveMemory):
    id: str = Field(min_length=1, max_length=64)


class Reminder(Args):
    title: str = Field(min_length=1, max_length=300)
    due_at: str
    project: str = Field(default="", max_length=200)
    timezone: str = "America/Sao_Paulo"
    done: bool = False
    importance: float = Field(default=0.5, ge=0, le=1)
    description: str = Field(default="", max_length=5000)
    priority: Literal["low", "normal", "high"] = "normal"
    calendar_event_id: str | None = Field(default=None, max_length=64)
    completed_at: str | None = Field(default=None, max_length=60)


class UpdateReminder(Reminder):
    id: str


class Path(Args):
    path: str = Field(min_length=1, max_length=300)


class Url(Args):
    url: str = Field(max_length=2000)


class Issue(Args):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(max_length=15000)


class Change(Path):
    content: str = Field(max_length=30000)
    message: str = Field(min_length=1, max_length=200)


class Calculation(Args):
    expression: str = Field(max_length=200)


class UpdateCalendar(CalendarEvent):
    id: str = Field(max_length=64)


class UpdateAlarm(Alarm):
    id: str = Field(max_length=64)


# name: (schema, description, approval required, integration)
REGISTRY = {
    "update_calendar_event": (
        UpdateCalendar,
        "Propor alteração de um evento existente e seus alarmes associados; exige aprovação da versão apresentada.",
        True,
        None,
    ),
    "update_alarm": (
        UpdateAlarm,
        "Propor alteração de alarme, fuso, modo e repetição; exige aprovação.",
        True,
        None,
    ),
    "get_current_time": (
        Empty,
        "Consultar data/hora UTC real e fuso inicial America/Sao_Paulo antes de interpretar amanhã, hoje ou horários relativos.",
        False,
        None,
    ),
    "list_calendar_events": (Empty, "Consultar eventos reais da agenda.", False, None),
    "create_calendar_event": (
        CalendarEvent,
        "Propor evento com início, fim, fuso e eventual alarme; exige aprovação. Sobreposições precisam de autorização explícita.",
        True,
        None,
    ),
    "delete_calendar_event": (
        Key,
        "Excluir evento e cancelar alarmes associados após aprovação.",
        True,
        None,
    ),
    "list_alarms": (
        Empty,
        "Consultar alarmes reais; não comprova entrega de notificação.",
        False,
        None,
    ),
    "create_alarm": (
        Alarm,
        "Propor alarme opcional com horário, fuso, repetição e mensagem; exige aprovação. PWA não garante disparo com app fechado.",
        True,
        None,
    ),
    "delete_alarm": (
        Key,
        "Excluir alarme e cancelar ocorrências pendentes após aprovação.",
        True,
        None,
    ),
    "list_voices": (
        Empty,
        "Consultar catálogo e configuração real de motores de voz; a reprodução é acionada na interface.",
        False,
        None,
    ),
    "calculate": (Calculation, "Calcular aritmética sem executar código.", False, None),
    "check_load": (
        LoadCheck,
        "Verificar soma de massas (g/kg), capacidade declarada e excesso em kg. Não confundir limite de carga com massa de um componente nem com volume de água.",
        False,
        None,
    ),
    "check_energy_cost": (
        EnergyCheck,
        "Verificar energia teórica em kWh e custo em BRL por potência W/kW, horas/dia, dias e tarifa BRL/kWh. Não é medição do consumo real.",
        False,
        None,
    ),
    "search_memory": (Query, "Consultar a memória global autorizada.", False, None),
    "save_memory": (SaveMemory, "Propor gravação na memória única; exige aprovação.", True, None),
    "update_memory": (UpdateMemory, "Propor correção de uma memória; exige aprovação.", True, None),
    "delete_memory": (Key, "Excluir memória e derivados após aprovação.", True, None),
    "search_smolin": (
        Query,
        "Pesquisar documentos do Centro Smolin com referências reais.",
        False,
        None,
    ),
    "get_document_excerpt": (Excerpt, "Ler um trecho documental por ID.", False, None),
    "list_documents": (Empty, "Listar documentos e seus estados reais.", False, None),
    "list_reminders": (Empty, "Consultar a agenda pessoal.", False, None),
    "create_reminder": (Reminder, "Propor um lembrete com horário explícito.", True, None),
    "update_reminder": (UpdateReminder, "Propor alteração de lembrete.", True, None),
    "delete_reminder": (Key, "Excluir lembrete após aprovação.", True, None),
    "search_web": (Query, "Pesquisar na web pela integração configurada.", False, "search"),
    "read_web_source": (Url, "Ler fonte pública HTTPS de domínio autorizado.", False, "web"),
    "search_github_repository": (
        Query,
        "Consultar issues do repositório GitHub autorizado.",
        False,
        "github",
    ),
    "read_github_file": (Path, "Ler arquivo do repositório autorizado.", False, "github"),
    "create_github_issue": (Issue, "Criar issue somente após aprovação.", True, "github"),
    "propose_github_change": (
        Change,
        "Propor alteração de arquivo com diff revisável e SHA protegido.",
        True,
        "github",
    ),
}


def availability(name):
    integration = REGISTRY[name][3]
    return (
        not integration
        or (integration == "github" and integrations.github_ready)
        or (integration == "search" and bool(integrations.search_key))
        or (integration == "web" and bool(integrations.web_hosts))
    )


def schemas(*, use_memory=True, use_knowledge=True):
    blocked = set()
    if not use_memory:
        blocked.add("search_memory")
    if not use_knowledge:
        blocked.update(("search_smolin", "list_documents", "get_document_excerpt"))
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": entry[1],
                "parameters": entry[0].model_json_schema(),
            },
        }
        for name, entry in REGISTRY.items()
        if availability(name) and name not in blocked
    ]


def validate(name, args):
    if name not in REGISTRY or not availability(name):
        raise ValueError("Ferramenta indisponível")
    return REGISTRY[name][0].model_validate(args).model_dump()


def normalized_reminder(args):
    from zoneinfo import ZoneInfo

    stamp = datetime.fromisoformat(args["due_at"])
    try:
        zone = ZoneInfo(args["timezone"])
    except (KeyError, ValueError):
        raise ValueError("Fuso horário inválido") from None
    if stamp.tzinfo is None:
        naive = stamp
        stamp = stamp.replace(tzinfo=zone)
        if stamp.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != naive:
            raise ValueError("Horário inexistente neste fuso")
        if stamp.replace(fold=0).utcoffset() != stamp.replace(fold=1).utcoffset():
            raise ValueError("Horário ambíguo: forneça um deslocamento UTC explícito")
    return {**args, "due_at": stamp.astimezone(UTC).isoformat()}


def completed_reminder(args, previous=None):
    data = normalized_reminder(args)
    if data.get("calendar_event_id") and not store.get(
        "calendar_events", data["calendar_event_id"]
    ):
        raise ValueError("Evento associado não encontrado")
    data["completed_at"] = (
        ((previous or {}).get("completed_at") if (previous or {}).get("done") else store.now())
        if data.get("done")
        else None
    )
    return data


async def execute(name, args):
    args = validate(name, args)
    if name == "get_current_time":
        from zoneinfo import ZoneInfo

        now = datetime.now(UTC)
        timezone = (
            store.setting("preferences", {}).get("notifications", {}).get("timezone")
            or "America/Sao_Paulo"
        )
        return {
            "utc": now.isoformat(),
            "timezone": timezone,
            "local": now.astimezone(ZoneInfo(timezone)).isoformat(),
        }
    if name == "list_calendar_events":
        return store.all_records("calendar_events")
    if name == "list_alarms":
        return store.all_records("alarms")
    if name == "create_calendar_event":
        return save_event(args)
    if name == "update_calendar_event":
        key = args.pop("id")
        if not store.get("calendar_events", key):
            raise ValueError("Evento não encontrado")
        return save_event(args, key)
    if name == "delete_calendar_event":
        delete_event(args["id"])
        return {"deleted": True}
    if name == "create_alarm":
        return save_alarm(args)
    if name == "update_alarm":
        key = args.pop("id")
        if not store.get("alarms", key):
            raise ValueError("Alarme não encontrado")
        return save_alarm(args, key)
    if name == "delete_alarm":
        delete_alarm(args["id"])
        return {"deleted": True}
    if name == "list_voices":
        return voice_catalog(True)
    if name == "check_load":
        return check_load(args)
    if name == "check_energy_cost":
        return check_energy_cost(args)
    if name == "calculate":
        return {"result": calculate(args["expression"]), "method": "bounded_ast"}
    if name == "search_memory":
        return (await search_memories(args["query"], usable=True))[:6]
    if name == "save_memory":
        result = memory_save(Memory(**args))
        await index_memory(result["id"])
        return result
    if name == "update_memory":
        result = memory_save(Memory(content=args["content"], category=args["category"]), args["id"])
        await index_memory(args["id"])
        return result
    if name == "delete_memory":
        memory_delete(args["id"])
        return {"deleted": True}
    if name == "search_smolin":
        return await smolin_search(args["query"])
    if name == "get_document_excerpt":
        from sqlalchemy import select

        with store.db() as c:
            r = (
                c.execute(select(store.chunks).where(store.chunks.c.id == args["chunk_id"]))
                .mappings()
                .first()
            )
        if not r:
            raise ValueError("Trecho não encontrado")
        return {k: r[k] for k in ("id", "document_id", "page", "position", "content")}
    if name == "list_documents":
        return [
            {k: d.get(k) for k in ("id", "name", "status", "page_count")}
            for d in store.all_records("documents")
        ]
    if name == "list_reminders":
        return store.all_records("reminders")
    if name in ("create_reminder", "update_reminder"):
        key = args.pop("id", None)
        current = store.get("reminders", key) if key else None
        if key and not current:
            raise ValueError("Lembrete não encontrado")
        return store.save("reminders", completed_reminder(args, current), key)
    if name == "delete_reminder":
        if not store.get("reminders", args["id"]):
            raise ValueError("Lembrete não encontrado")
        store.remove("reminders", args["id"])
        return {"deleted": True}
    if name == "search_web":
        return await integrations.search_web(args["query"])
    if name == "read_web_source":
        return await integrations.read_web(args["url"])
    if name == "search_github_repository":
        issues = await integrations.github("GET", "/issues?state=all&per_page=50")
        return [
            {"number": i["number"], "title": i["title"], "url": i["html_url"]}
            for i in issues
            if args["query"].casefold() in i["title"].casefold()
        ][:10]
    if name == "read_github_file":
        return await integrations.read_file(args["path"])
    if name == "create_github_issue":
        result = await integrations.github("POST", "/issues", args)
        return {"number": result["number"], "url": result["html_url"]}
    raise ValueError("Ferramenta desconhecida")


async def request_tool(name, args, conversation_id=None):
    validated = validate(name, args)
    if name in ("create_reminder", "update_reminder"):
        validated = normalized_reminder(validated)
    if name in {"create_calendar_event", "update_calendar_event"}:
        key = validated.pop("id", None)
        validated = normalized_event(validated)
        if key:
            validated["id"] = key
    if name in {"create_alarm", "update_alarm"}:
        key = validated.pop("id", None)
        validated = normalized_alarm(validated)
        if key:
            validated["id"] = key
    execution = store.save(
        "tool_executions",
        {
            "tool_name": name,
            "argument_names": list(validated),
            "status": "started",
            "conversation_id": conversation_id,
        },
    )
    if REGISTRY[name][2]:
        preview = None
        if name in {
            "delete_calendar_event",
            "update_calendar_event",
            "delete_alarm",
            "update_alarm",
        }:
            kind = (
                "calendar_events"
                if name in {"delete_calendar_event", "update_calendar_event"}
                else "alarms"
            )
            target = store.get(kind, validated["id"])
            if not target:
                raise ValueError("Registro não encontrado")
            preview = {
                "kind": kind,
                "id": target["id"],
                "updated": target["updated"],
                "summary": target["title"],
            }
        if name == "create_alarm" and validated.get("linked_event_id"):
            target = store.get("calendar_events", validated["linked_event_id"])
            preview = {
                "kind": "calendar_events",
                "id": target["id"],
                "updated": target["updated"],
                "summary": target["title"] + " · " + target["start_at"],
            }
        if name in ("delete_memory", "update_memory", "delete_reminder", "update_reminder"):
            kind = "memories" if "memory" in name else "reminders"
            target = store.get(kind, validated["id"])
            if not target:
                raise ValueError("Registro não encontrado")
            preview = {
                "kind": kind,
                "id": target["id"],
                "updated": target["updated"],
                "summary": target.get("content", target.get("title", ""))[:1500],
            }

        if name == "propose_github_change":
            import difflib

            try:
                before = await integrations.read_file(validated["path"])
            except Exception:
                store.save("tool_executions", {**execution, "status": "failed"}, execution["id"])
                raise
            preview = {
                "sha": before["sha"],
                "diff": "\n".join(
                    difflib.unified_diff(
                        before["content"].splitlines(),
                        validated["content"].splitlines(),
                        fromfile=validated["path"],
                        tofile=validated["path"],
                    )
                ),
            }
        approval = store.save(
            "agent_approvals",
            {
                "tool_name": name,
                "arguments": validated,
                "execution_id": execution["id"],
                "status": "pending",
                "preview": preview,
                "conversation_id": conversation_id,
            },
        )
        store.save(
            "tool_executions",
            {**execution, "status": "approval_required", "approval_id": approval["id"]},
            execution["id"],
        )
        return {
            "approval_required": True,
            "approval_id": approval["id"],
            "execution_id": execution["id"],
            "executed": False,
        }
    try:
        result = await execute(name, validated)
        store.save("tool_executions", {**execution, "status": "completed"}, execution["id"])
        store.audit("tool", "Consulta concluída: " + name)
        return {"executed": True, "result": result, "execution_id": execution["id"]}
    except asyncio.CancelledError:
        store.save("tool_executions", {**execution, "status": "cancelled"}, execution["id"])
        raise
    except Exception:
        store.save("tool_executions", {**execution, "status": "failed"}, execution["id"])
        raise


async def decide(key, approve):
    approval = store.get("agent_approvals", key)
    if not approval or approval["status"] != "pending":
        raise HTTPException(409, "Aprovação indisponível ou já utilizada")
    if (datetime.now(UTC) - datetime.fromisoformat(approval["created"])).total_seconds() > 900:
        store.save("agent_approvals", {**approval, "status": "expired"}, key)
        raise HTTPException(409, "Aprovação expirada")
    status = "running" if approve else "rejected"
    with store.db() as c:
        updated = c.execute(
            update(store.tables["agent_approvals"])
            .where(
                store.tables["agent_approvals"].c.id == key,
                store.tables["agent_approvals"].c.data["status"].as_string() == "pending",
            )
            .values(
                data={
                    k: v
                    for k, v in {**approval, "status": status}.items()
                    if k not in ("id", "created", "updated")
                }
            )
        )
        if updated.rowcount != 1:
            raise HTTPException(409, "Aprovação já consumida")
    execution = store.get("tool_executions", approval["execution_id"])
    if not approve:
        store.save("tool_executions", {**execution, "status": "rejected"}, execution["id"])
        return {"status": "rejected"}
    try:
        preview = approval.get("preview")
        if preview and preview.get("kind"):
            current = store.get(preview["kind"], preview["id"])
            if not current or current["updated"] != preview["updated"]:
                raise ValueError("Registro alterado após a proposta; revise uma nova operação")
        if approval["tool_name"] == "propose_github_change":
            import base64

            args = approval["arguments"]
            preview = approval["preview"]
            current = await integrations.read_file(args["path"])
            if current["sha"] != preview["sha"]:
                raise ValueError("O arquivo mudou; gere nova proposta para revisar o diff")
            from urllib.parse import quote

            response = await integrations.github(
                "PUT",
                "/contents/" + quote(args["path"], safe="/"),
                {
                    "message": args["message"],
                    "content": base64.b64encode(args["content"].encode()).decode(),
                    "sha": preview["sha"],
                },
            )
            result = {"commit": response["commit"]["sha"]}
        else:
            result = await execute(approval["tool_name"], approval["arguments"])
        store.save("agent_approvals", {**approval, "status": "completed", "result": result}, key)
        store.save("tool_executions", {**execution, "status": "completed"}, execution["id"])
        store.audit("approval", "Operação aprovada e concluída: " + approval["tool_name"])
        return {"status": "completed", "result": result}
    except Exception:  # noqa: BLE001 - sanitize errors at the untrusted operation boundary
        store.save("agent_approvals", {**approval, "status": "failed"}, key)
        store.save("tool_executions", {**execution, "status": "failed"}, execution["id"])
        raise HTTPException(
            502,
            "Operação não confirmada. Não será repetida automaticamente; confira o destino antes de uma nova tentativa.",
        ) from None
