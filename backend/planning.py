"""Calendar and persistent alarm scheduler. No promise of exact/native background alarms."""

import asyncio
import hashlib
import secrets
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import storage as store
from .security import owner, throttle
from .timeutils import instant, next_occurrence, recurrence, zone

router = APIRouter(prefix="/api", tags=["planning"])
SCHEDULER_STATE = {"running": False, "last_check": None, "last_error": None}


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalendarEvent(Args):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)
    start_at: str = Field(max_length=60)
    end_at: str = Field(max_length=60)
    timezone: str = Field(default="America/Sao_Paulo", max_length=100)
    location: str = Field(default="", max_length=300)
    category: str = Field(default="pessoal", max_length=60)
    color: str = Field(default="#7acfc1", pattern=r"^#[0-9a-fA-F]{6}$")
    priority: Literal["low", "normal", "high"] = "normal"
    recurrence_rule: str | None = Field(default=None, max_length=300)
    notes: str = Field(default="", max_length=5000)
    checklist: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["scheduled", "completed", "cancelled"] = "scheduled"
    all_day: bool = False
    alarm_minutes_before: int | None = Field(default=None, ge=0, le=10080)
    allow_conflicts: bool = False

    @model_validator(mode="after")
    def validate_times(self):
        start, end = instant(self.start_at, self.timezone), instant(self.end_at, self.timezone)
        if not 1900 <= start.year <= 2200 or not start < end or end - start > timedelta(days=366):
            raise ValueError("Intervalo do evento inválido ou acima de um ano")
        recurrence(self.recurrence_rule, start, self.timezone)
        return self


class Alarm(Args):
    title: str = Field(min_length=1, max_length=300)
    message: str = Field(default="", max_length=1000)
    scheduled_at: str = Field(max_length=60)
    timezone: str = Field(default="America/Sao_Paulo", max_length=100)
    recurrence_rule: str | None = Field(default=None, max_length=300)
    enabled: bool = True
    mode: Literal["tone", "voice", "tone_voice", "silent"] = "tone"
    sound_id: Literal["soft", "bell", "pulse"] = "soft"
    priority: Literal["low", "normal", "high"] = "normal"
    snooze_minutes: int = Field(default=5, ge=1, le=120)
    linked_event_id: str | None = Field(default=None, max_length=64)
    linked_event_revision: int | None = Field(default=None, ge=1)
    offset_minutes: int = Field(default=0, ge=0, le=10080)

    @model_validator(mode="after")
    def validate_times(self):
        start = instant(self.scheduled_at, self.timezone)
        if not 2000 <= start.year <= 2200:
            raise ValueError("Alarme deve estar entre os anos 2000 e 2200")
        recurrence(self.recurrence_rule, start, self.timezone)
        return self


def normalized_event(arguments):
    body = CalendarEvent.model_validate(arguments)
    return {
        **body.model_dump(),
        "start_at": (
            instant(body.start_at, body.timezone).replace(microsecond=0)
            if body.recurrence_rule
            else instant(body.start_at, body.timezone)
        ).isoformat(),
        "end_at": (
            instant(body.end_at, body.timezone).replace(microsecond=0)
            if body.recurrence_rule
            else instant(body.end_at, body.timezone)
        ).isoformat(),
        "recurrence_rule": body.recurrence_rule.upper() if body.recurrence_rule else None,
    }


def normalized_alarm(arguments):
    body = Alarm.model_validate(arguments)
    data = {
        **body.model_dump(),
        "scheduled_at": (
            instant(body.scheduled_at, body.timezone).replace(microsecond=0)
            if body.recurrence_rule
            else instant(body.scheduled_at, body.timezone)
        ).isoformat(),
        "recurrence_rule": body.recurrence_rule.upper() if body.recurrence_rule else None,
    }
    if body.linked_event_id:
        event = store.get("calendar_events", body.linked_event_id)
        if not event:
            raise ValueError("Evento associado não encontrado")
        if body.linked_event_revision and body.linked_event_revision != event["revision"]:
            raise ValueError("Evento associado mudou após a revisão")
        data.update(
            scheduled_at=(
                instant(event["start_at"], event["timezone"])
                - timedelta(minutes=body.offset_minutes)
            ).isoformat(),
            timezone=event["timezone"],
            recurrence_rule=None,
            linked_event_revision=event["revision"],
        )
    return data


def alarm_next(alarm, after):
    if alarm.get("linked_event_id"):
        event = store.get("calendar_events", alarm["linked_event_id"])
        if not event or event["status"] == "cancelled":
            return None
        lead = timedelta(minutes=alarm.get("offset_minutes", 0))
        value = next_occurrence(
            instant(event["start_at"], event["timezone"]),
            event["timezone"],
            event.get("recurrence_rule"),
            after + lead,
        )
        return value - lead if value else None
    return next_occurrence(
        instant(alarm["scheduled_at"], alarm["timezone"]),
        alarm["timezone"],
        alarm.get("recurrence_rule"),
        after,
    )


def event_instances(record, start, end):
    origin = instant(record["start_at"], record["timezone"])
    duration = instant(record["end_at"], record["timezone"]) - origin
    calendar_days = (
        instant(record["end_at"], record["timezone"]).astimezone(zone(record["timezone"])).date()
        - origin.astimezone(zone(record["timezone"])).date()
    ).days
    probe = next_occurrence(
        origin,
        record["timezone"],
        record.get("recurrence_rule"),
        start - duration - timedelta(microseconds=1),
    )
    result = []
    while probe and probe < end and len(result) < 400:
        occurrence_end = (
            datetime.combine(
                probe.astimezone(zone(record["timezone"])).date()
                + timedelta(days=max(1, calendar_days)),
                time.min,
                zone(record["timezone"]),
            ).astimezone(UTC)
            if record.get("all_day")
            else probe + duration
        )
        if occurrence_end > start:
            result.append(
                {
                    **record,
                    "instance_id": record["id"] + "@" + probe.isoformat(),
                    "instance_start_at": probe.isoformat(),
                    "instance_end_at": occurrence_end.isoformat(),
                }
            )
        probe = next_occurrence(origin, record["timezone"], record.get("recurrence_rule"), probe)
    return result


def conflicts(data, exclude=None):
    proposed = {**data, "id": "proposal"}
    start = instant(data["start_at"], data["timezone"])
    end = start + timedelta(days=90)
    proposed_instances = event_instances(proposed, start, end)
    found = []
    for event in store.all_records("calendar_events"):
        if event["id"] == exclude or event["status"] != "scheduled":
            continue
        for instance in event_instances(event, start, end):
            for other in proposed_instances:
                if (
                    instance["instance_start_at"] < other["instance_end_at"]
                    and other["instance_start_at"] < instance["instance_end_at"]
                ):
                    found.append(
                        {
                            "id": event["id"],
                            "title": event["title"],
                            "start_at": instance["instance_start_at"],
                            "end_at": instance["instance_end_at"],
                        }
                    )
                    break
    return found[:100]


def save_alarm(arguments, key=None):
    data = normalized_alarm(arguments)
    # Start with the first configured occurrence; startup tick classifies overdue work.
    data["next_due_at"] = data["scheduled_at"] if data["enabled"] else None
    with store.transaction():
        previous = store.get("alarms", key) if key else None
        if previous and any(
            previous.get(field) != data.get(field)
            for field in (
                "scheduled_at",
                "timezone",
                "recurrence_rule",
                "linked_event_id",
                "offset_minutes",
            )
        ):
            cancel_occurrences(key)
        saved = store.save("alarms", data, key)
        if not data["enabled"]:
            cancel_occurrences(saved["id"])
        store.audit("alarm", "Alarme configurado: " + saved["id"])
        return saved


def save_event(arguments, key=None):
    data = normalized_event(arguments)
    with store.transaction():
        if not data["allow_conflicts"] and conflicts(data, key):
            raise HTTPException(
                409,
                "Conflito nos próximos 90 dias. Revise a prévia e autorize sobreposição se desejada.",
            )
        previous = store.get("calendar_events", key) if key else None
        saved = store.save("calendar_events", data, key)
        alarm_id = previous.get("alarm_id") if previous else None
        if data["alarm_minutes_before"] is not None:
            alarm = save_alarm(
                {
                    "title": data["title"],
                    "message": data["description"][:1000],
                    "scheduled_at": data["start_at"],
                    "timezone": data["timezone"],
                    "linked_event_id": saved["id"],
                    "linked_event_revision": saved["revision"],
                    "offset_minutes": data["alarm_minutes_before"],
                    "enabled": data["status"] == "scheduled",
                },
                alarm_id,
            )
            saved = store.save("calendar_events", {**saved, "alarm_id": alarm["id"]}, saved["id"])
            # This internal link-only write must not make the just-created alarm stale.
            store.save("alarms", {**alarm, "linked_event_revision": saved["revision"]}, alarm["id"])
        elif alarm_id:
            alarm = store.get("alarms", alarm_id)
            if alarm:
                store.save("alarms", {**alarm, "enabled": False, "next_due_at": None}, alarm_id)
                cancel_occurrences(alarm_id)
        for linked in store.all_records("alarms"):
            if linked.get("linked_event_id") != saved["id"] or linked["id"] == saved.get(
                "alarm_id"
            ):
                continue
            scheduled = instant(data["start_at"], data["timezone"]) - timedelta(
                minutes=linked.get("offset_minutes", 0)
            )
            if (
                linked["scheduled_at"] != scheduled.isoformat()
                or (previous and previous.get("recurrence_rule") != data.get("recurrence_rule"))
                or data["status"] != "scheduled"
            ):
                cancel_occurrences(linked["id"])
            enabled = linked["enabled"] and data["status"] == "scheduled"
            store.save(
                "alarms",
                {
                    **linked,
                    "scheduled_at": scheduled.isoformat(),
                    "timezone": data["timezone"],
                    "linked_event_revision": saved["revision"],
                    "next_due_at": scheduled.isoformat() if enabled else None,
                    "enabled": enabled,
                },
                linked["id"],
            )
        return saved


def cancel_occurrences(alarm_id):
    for item in store.all_records("alarm_occurrences"):
        if item["alarm_id"] == alarm_id and item["status"] in {"queued", "pending", "claimed"}:
            store.save("alarm_occurrences", {**item, "status": "cancelled"}, item["id"])


def delete_alarm(key):
    if not store.get("alarms", key):
        raise HTTPException(404, "Alarme não encontrado")
    with store.transaction():
        cancel_occurrences(key)
        store.remove("alarms", key)
        store.audit("alarm_delete", "Alarme excluído: " + key)


def delete_event(key):
    if not store.get("calendar_events", key):
        raise HTTPException(404, "Evento não encontrado")
    with store.transaction():
        for alarm in store.all_records("alarms"):
            if alarm.get("linked_event_id") == key:
                store.save("alarms", {**alarm, "enabled": False, "next_due_at": None}, alarm["id"])
                cancel_occurrences(alarm["id"])
        store.remove("calendar_events", key)


def tick(now=None):
    current = now or datetime.now(UTC)
    due = [
        alarm
        for alarm in store.all_records("alarms")
        if alarm.get("enabled")
        and alarm.get("next_due_at")
        and instant(alarm["next_due_at"], "UTC") <= current
    ][:200]
    for alarm in due:
        with store.transaction():
            fresh = store.get("alarms", alarm["id"])
            if (
                not fresh
                or not fresh["enabled"]
                or fresh.get("next_due_at") != alarm["next_due_at"]
            ):
                continue
            scheduled = instant(fresh["next_due_at"], "UTC")
            key = hashlib.sha256((fresh["id"] + "@" + scheduled.isoformat()).encode()).hexdigest()
            if not store.get("alarm_occurrences", key):
                store.save(
                    "alarm_occurrences",
                    {
                        "alarm_id": fresh["id"],
                        "title": fresh["title"],
                        "message": fresh["message"],
                        "scheduled_at": scheduled.isoformat(),
                        "status": "pending"
                        if (current - scheduled).total_seconds() <= 300
                        else "missed",
                        "mode": fresh["mode"],
                        "sound_id": fresh["sound_id"],
                        "priority": fresh["priority"],
                        "snooze_minutes": fresh["snooze_minutes"],
                        "delivery": "not_delivered",
                    },
                    key,
                )
            following = alarm_next(fresh, current)
            store.save(
                "alarms",
                {
                    **fresh,
                    "next_due_at": following.isoformat() if following else None,
                    "enabled": bool(following),
                },
                fresh["id"],
            )
    for item in store.all_records("alarm_occurrences"):
        if (
            item["status"] in {"pending", "claimed"}
            and (current - instant(item["scheduled_at"], "UTC")).total_seconds() > 300
        ):
            store.save(
                "alarm_occurrences",
                {
                    **item,
                    "status": "missed",
                    "delivery": "not_confirmed",
                    "missed_at": current.isoformat(),
                },
                item["id"],
            )
            continue
        if item["status"] == "queued" and instant(item["scheduled_at"], "UTC") <= current:
            store.save(
                "alarm_occurrences",
                {
                    **item,
                    "status": "pending"
                    if (current - instant(item["scheduled_at"], "UTC")).total_seconds() <= 300
                    else "missed",
                },
                item["id"],
            )


async def scheduler():
    SCHEDULER_STATE["running"] = True
    try:
        while True:
            try:
                await asyncio.to_thread(tick)
                SCHEDULER_STATE.update(last_check=store.now(), last_error=None)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - keep scheduler alive without logging personal content
                SCHEDULER_STATE["last_error"] = "check_not_confirmed"
                try:
                    store.audit(
                        "alarm_error",
                        "Agendador não confirmou esta consulta; verificará novamente.",
                    )
                except Exception:  # noqa: BLE001 - database outage must not terminate future retries
                    SCHEDULER_STATE["last_error"] = "audit_unavailable"
            await asyncio.sleep(15)
    finally:
        SCHEDULER_STATE["running"] = False


class EventWrite(Args):
    data: CalendarEvent
    base_revision: int = Field(default=0, ge=0)
    confirm: bool = False


class AlarmWrite(Args):
    data: Alarm
    base_revision: int = Field(default=0, ge=0)
    confirm: bool = False


def check_write(kind, key, revision, confirmed):
    if not confirmed:
        raise HTTPException(400, "Confirme o alvo, horário e conteúdo antes de salvar")
    current = store.get(kind, key) if key else None
    if key and (not current or current["revision"] != revision):
        raise HTTPException(409, "Registro alterado ou excluído; carregue a versão atual")


@router.get("/calendar/events")
def events(_=Depends(owner)):
    return store.all_records("calendar_events")


@router.post("/calendar/preview")
def preview_event(body: EventWrite, key: str | None = None, _=Depends(owner)):
    data = normalized_event(body.data.model_dump())
    return {
        "event": data,
        "conflicts": conflicts(data, key),
        "scope": "Conflitos verificados nos próximos 90 dias a partir do início proposto.",
    }


@router.post("/calendar/events")
def create_event(body: EventWrite, _=Depends(owner)):
    check_write("calendar_events", None, 0, body.confirm)
    return save_event(body.data.model_dump())


@router.patch("/calendar/events/{key}")
def update_event(key: str, body: EventWrite, _=Depends(owner)):
    with store.transaction():
        check_write("calendar_events", key, body.base_revision, body.confirm)
        return save_event(body.data.model_dump(), key)


@router.delete("/calendar/events/{key}")
def remove_event(key: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(
            400, "Confirme a exclusão do evento e cancelamento dos alarmes associados"
        )
    delete_event(key)
    return {"deleted": True}


@router.get("/calendar/instances")
def instances(
    date_from: date, date_to: date, timezone: str = "America/Sao_Paulo", _=Depends(owner)
):
    if not 0 < (date_to - date_from).days <= 366:
        raise HTTPException(422, "Escolha um intervalo de até 366 dias")
    start = datetime.combine(date_from, time.min, zone(timezone)).astimezone(UTC)
    end = datetime.combine(date_to, time.min, zone(timezone)).astimezone(UTC)
    result = []
    for record in store.all_records("calendar_events"):
        if record["status"] != "cancelled":
            result.extend(event_instances(record, start, end))
    return sorted(result, key=lambda item: item["instance_start_at"])[:2000]


@router.get("/alarms")
def alarms(_=Depends(owner)):
    return store.all_records("alarms")


@router.post("/alarms/preview")
def preview_alarm(body: AlarmWrite, _=Depends(owner)):
    data = normalized_alarm(body.data.model_dump())
    first = instant(data["scheduled_at"], "UTC")
    result = [first.isoformat()]
    following = first
    for _ in range(4):
        following = alarm_next(data, following)
        if not following:
            break
        result.append(following.isoformat())
    return {
        "alarm": data,
        "next_occurrences": result,
        "capability": "alarme_na_interface",
        "warning": "PWA não garante horário exato com navegador fechado/offline. Backend precisa permanecer ativo; Push e alarme nativo não estão configurados.",
    }


@router.post("/alarms")
def create_alarm(body: AlarmWrite, _=Depends(owner)):
    check_write("alarms", None, 0, body.confirm)
    return save_alarm(body.data.model_dump())


@router.patch("/alarms/{key}")
def update_alarm(key: str, body: AlarmWrite, _=Depends(owner)):
    with store.transaction():
        check_write("alarms", key, body.base_revision, body.confirm)
        return save_alarm(body.data.model_dump(), key)


@router.delete("/alarms/{key}")
def remove_alarm(key: str, confirm: bool = False, _=Depends(owner)):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão do alarme")
    delete_alarm(key)
    return {"deleted": True}


@router.get("/alarms/occurrences")
def occurrences(active: bool = False, _=Depends(owner)):
    items = store.all_records("alarm_occurrences")
    return [
        item
        for item in items
        if not active or item["status"] in {"pending", "claimed", "presented"}
    ][:300]


@router.get("/notifications/capabilities")
def notification_capabilities(_=Depends(owner)):
    return {
        "alarme_na_interface": True,
        "push_configurado": False,
        "alarme_nativo": False,
        "exact_alarm": False,
        "scheduler": "backend_persistente_enquanto_processo_ativo",
        "scheduler_observed": dict(SCHEDULER_STATE),
        "poll_seconds": 15,
        "late_policy": "Até 5 minutos: pendente; mais antigo: perdido. Repetições intermediárias durante indisponibilidade não são notificadas como se tivessem sido entregues.",
        "warning": "Não é despertador nativo. Sem garantia de execução offline/com navegador encerrado ou servidor suspenso.",
    }


class NotificationTest(Args):
    confirm: bool = False
    mode: Literal["tone", "voice", "tone_voice", "silent"] = "silent"


@router.post("/notifications/test")
def test_notification(body: NotificationTest, _=Depends(owner)):
    throttle("test-alarm", 3)
    if not body.confirm:
        raise HTTPException(400, "Confirme o teste de apresentação de alarme")
    now = datetime.now(UTC)
    alarm = save_alarm(
        {
            "title": "Teste de alarme SALY",
            "message": "Este é um teste de apresentação na interface aberta.",
            "scheduled_at": now.isoformat(),
            "timezone": "UTC",
            "mode": body.mode,
        }
    )
    tick(now)
    return {
        "alarm_id": alarm["id"],
        "status": "scheduled",
        "scope": "Ocorrência real criada no banco; aguarda apresentação pela interface autorizada, não é uma confirmação de entrega.",
    }


@router.post("/alarm-occurrences/{key}/claim")
def claim_occurrence(key: str, _=Depends(owner)):
    throttle("alarm-claim", 60)
    with store.transaction():
        item = store.get("alarm_occurrences", key)
        now = datetime.now(UTC)
        if not item or (
            item["status"] != "pending"
            and not (item["status"] == "claimed" and instant(item["lease_until"], "UTC") < now)
        ):
            raise HTTPException(409, "Ocorrência já apresentada ou sendo processada")
        token = secrets.token_urlsafe(24)
        store.save(
            "alarm_occurrences",
            {
                **item,
                "status": "claimed",
                "claim_hash": hashlib.sha256(token.encode()).hexdigest(),
                "lease_until": (now + timedelta(seconds=30)).isoformat(),
            },
            key,
        )
        return {
            "occurrence": {k: v for k, v in item.items() if k != "claim_hash"},
            "claim_token": token,
        }


class Presentation(Args):
    claim_token: str = Field(max_length=100)
    notification_requested: bool = False
    audio_started: bool = False
    voice_requested: bool = False


@router.post("/alarm-occurrences/{key}/presented")
def mark_presented(key: str, body: Presentation, _=Depends(owner)):
    with store.transaction():
        item = store.get("alarm_occurrences", key)
        if (
            not item
            or item["status"] != "claimed"
            or not secrets.compare_digest(
                item["claim_hash"], hashlib.sha256(body.claim_token.encode()).hexdigest()
            )
        ):
            raise HTTPException(409, "Confirmação de apresentação inválida ou já utilizada")
        store.save(
            "alarm_occurrences",
            {
                **item,
                "status": "presented",
                "delivery": "ui_reported",
                "presented_at": store.now(),
                "notification_requested": body.notification_requested,
                "audio_started": body.audio_started,
                "voice_requested": body.voice_requested,
            },
            key,
        )
        return {
            "status": "presented",
            "scope": "Interface reportou apresentação; não comprova entrega física pelo sistema operacional ou alto-falante.",
        }


class Snooze(Args):
    minutes: int = Field(default=5, ge=1, le=120)


@router.post("/alarm-occurrences/{key}/snooze")
def snooze_occurrence(key: str, body: Snooze, _=Depends(owner)):
    with store.transaction():
        item = store.get("alarm_occurrences", key)
        if not item or item["status"] not in {"pending", "claimed", "presented"}:
            raise HTTPException(409, "Ocorrência não pode ser adiada novamente")
        scheduled = datetime.now(UTC) + timedelta(minutes=body.minutes)
        saved = store.save(
            "alarm_occurrences",
            {
                **{
                    k: v
                    for k, v in item.items()
                    if k
                    not in {
                        "id",
                        "created",
                        "updated",
                        "claim_hash",
                        "lease_until",
                        "presented_at",
                        "notification_requested",
                        "audio_started",
                        "voice_requested",
                        "snoozed_to",
                        "dismissed_at",
                    }
                },
                "status": "queued",
                "scheduled_at": scheduled.isoformat(),
                "parent_id": key,
                "delivery": "not_delivered",
            },
        )
        store.save(
            "alarm_occurrences", {**item, "status": "snoozed", "snoozed_to": saved["id"]}, key
        )
        return saved


@router.post("/alarm-occurrences/{key}/dismiss")
def dismiss_occurrence(key: str, _=Depends(owner)):
    with store.transaction():
        item = store.get("alarm_occurrences", key)
        if not item or item["status"] not in {"pending", "claimed", "presented", "missed"}:
            raise HTTPException(409, "Ocorrência indisponível ou já concluída")
        return store.save(
            "alarm_occurrences", {**item, "status": "dismissed", "dismissed_at": store.now()}, key
        )
