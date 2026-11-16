"""Explicit instants and bounded civil-time recurrences, including DST rejection."""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr


def zone(name):
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError):
        raise ValueError("Fuso horário inválido") from None


def instant(value, timezone):
    stamp = datetime.fromisoformat(value)
    target = zone(timezone)
    if stamp.tzinfo is None:
        naive = stamp
        stamp = stamp.replace(tzinfo=target)
        if stamp.astimezone(UTC).astimezone(target).replace(tzinfo=None) != naive:
            raise ValueError("Horário inexistente neste fuso")
        if stamp.replace(fold=0).utcoffset() != stamp.replace(fold=1).utcoffset():
            raise ValueError("Horário ambíguo: forneça um deslocamento UTC explícito")
    return stamp.astimezone(UTC)


def recurrence(rule, start, timezone):
    if not rule:
        return None
    values = {}
    for part in rule.upper().split(";"):
        if "=" not in part:
            raise ValueError("Recorrência inválida")
        key, value = part.split("=", 1)
        if key in values:
            raise ValueError("Campo duplicado na recorrência")
        values[key] = value
    if values.get("FREQ") not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
        raise ValueError("Use recorrência diária, semanal, mensal ou anual")
    if set(values) - {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "COUNT", "UNTIL"}:
        raise ValueError("Campo de recorrência não suportado")
    for name, maximum in [("INTERVAL", 365), ("COUNT", 10000)]:
        if name in values and (
            not re.fullmatch(r"\d{1,5}", values[name]) or not 1 <= int(values[name]) <= maximum
        ):
            raise ValueError("Intervalo/contagem de recorrência fora do limite")
    if "BYDAY" in values and any(
        day not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"} for day in values["BYDAY"].split(",")
    ):
        raise ValueError("Dias da semana inválidos")
    if "BYMONTHDAY" in values and any(
        not re.fullmatch(r"-?\d{1,2}", day) or int(day) == 0 or abs(int(day)) > 31
        for day in values["BYMONTHDAY"].split(",")
    ):
        raise ValueError("Dia do mês inválido")
    if "UNTIL" in values and not re.fullmatch(r"\d{8}T\d{6}Z", values["UNTIL"]):
        raise ValueError("UNTIL deve ser um instante UTC YYYYMMDDTHHMMSSZ")
    if "UNTIL" in values and "COUNT" in values:
        raise ValueError("Escolha UNTIL ou COUNT, não os dois")
    local = start.astimezone(zone(timezone)).replace(microsecond=0)
    if not valid_civil_time(local):
        raise ValueError(
            "A recorrência não pode iniciar em horário civil ambíguo; escolha outro início"
        )
    result = rrulestr(
        ";".join(f"{key}={value}" for key, value in values.items()),
        dtstart=local,
    )
    first = result.after(local - timedelta(microseconds=1), inc=True)
    if first is None or first.astimezone(UTC) != start.replace(microsecond=0):
        raise ValueError("A data inicial deve corresponder ao padrão de repetição")
    return result


def valid_civil_time(value):
    target = value.tzinfo
    return (
        value.astimezone(UTC).astimezone(target).replace(tzinfo=None) == value.replace(tzinfo=None)
        and value.replace(fold=0).utcoffset() == value.replace(fold=1).utcoffset()
    )


def next_occurrence(start, timezone, rule, after):
    if not rule:
        return start if start > after else None
    iterator = recurrence(rule, start, timezone)
    value = iterator.after(after.astimezone(zone(timezone)), inc=False)
    for _ in range(10):
        if value is None:
            return None
        if valid_civil_time(value):
            return value.astimezone(UTC)
        value = iterator.after(value, inc=False)
    raise ValueError("Recorrência não produziu horário civil válido")
