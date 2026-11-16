import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from backend import planning
from backend import storage as store
from backend.timeutils import instant, next_occurrence


def event(**values):
    return {
        "title": "Estudo",
        "start_at": "2026-11-17T13:00",
        "end_at": "2026-11-17T14:00",
        "timezone": "America/Sao_Paulo",
        **values,
    }


def alarm(**values):
    return {
        "title": "Revisar Biologia",
        "scheduled_at": "2026-11-17T13:00",
        "timezone": "America/Sao_Paulo",
        **values,
    }


def test_calendar_crud_conflicts_revision_and_linked_alarm(client):
    value = event(alarm_minutes_before=15)
    preview = client.post("/api/calendar/preview", json={"data": value}).json()
    assert not preview["conflicts"] and preview["event"]["start_at"].startswith("2026-11-17T16:00")
    assert client.post("/api/calendar/events", json={"data": value}).status_code == 400
    created = client.post("/api/calendar/events", json={"data": value, "confirm": True})
    assert created.status_code == 200, created.text
    saved = created.json()
    associated = store.get("alarms", saved["alarm_id"])
    assert associated["scheduled_at"].startswith("2026-11-17T15:45")
    extra = client.post(
        "/api/alarms",
        json={
            "data": alarm(
                linked_event_id=saved["id"],
                linked_event_revision=saved["revision"],
                offset_minutes=5,
            ),
            "confirm": True,
        },
    ).json()
    overlaps = client.post(
        "/api/calendar/preview",
        json={"data": event(start_at="2026-11-17T13:30", end_at="2026-11-17T14:30")},
    ).json()
    assert overlaps["conflicts"][0]["id"] == saved["id"]
    assert (
        client.post("/api/calendar/events", json={"data": event(), "confirm": True}).status_code
        == 409
    )
    updated = {
        "data": event(
            title="Revisão",
            start_at="2026-11-18T10:00",
            end_at="2026-11-18T11:00",
            alarm_minutes_before=30,
        ),
        "base_revision": saved["revision"],
        "confirm": True,
    }
    result = client.patch("/api/calendar/events/" + saved["id"], json=updated)
    assert result.status_code == 200, result.text
    assert store.get("alarms", saved["alarm_id"])["scheduled_at"].startswith("2026-11-18T12:30")
    assert store.get("alarms", extra["id"])["scheduled_at"].startswith("2026-11-18T12:55")
    assert client.patch("/api/calendar/events/" + saved["id"], json=updated).status_code == 409
    assert (
        client.delete(
            "/api/calendar/events/" + saved["id"] + "?confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert not store.get("alarms", saved["alarm_id"])["enabled"]


def test_calendar_instances_weekly_and_month_end_are_real(client):
    weekly = client.post(
        "/api/calendar/events",
        json={"data": event(recurrence_rule="FREQ=WEEKLY;COUNT=3"), "confirm": True},
    )
    assert weekly.status_code == 200, weekly.text
    result = client.get(
        "/api/calendar/instances?date_from=2026-11-16&date_to=2026-12-08&timezone=America/Sao_Paulo"
    ).json()
    assert [item["instance_start_at"][:10] for item in result] == [
        "2026-11-17",
        "2026-11-24",
        "2026-12-01",
    ]
    start = instant("2026-01-31T10:00", "America/Sao_Paulo")
    assert next_occurrence(start, "America/Sao_Paulo", "FREQ=MONTHLY", start).day == 31
    assert next_occurrence(start, "America/Sao_Paulo", "FREQ=MONTHLY", start).month == 3


def test_dst_gaps_ambiguity_and_bounded_recurrence_are_checked(client):
    with pytest.raises(ValueError, match="inexistente"):
        instant("2026-03-08T02:30", "America/New_York")
    with pytest.raises(ValueError, match="ambíguo"):
        instant("2026-11-01T01:30", "America/New_York")
    start = instant("2026-03-01T02:30", "America/New_York")
    assert next_occurrence(start, "America/New_York", "FREQ=WEEKLY", start) == datetime(
        2026, 3, 15, 6, 30, tzinfo=UTC
    )
    assert (
        client.post(
            "/api/alarms/preview", json={"data": alarm(recurrence_rule="FREQ=SECONDLY")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/alarms/preview", json={"data": alarm(recurrence_rule="FREQ=DAILY;COUNT=999999")}
        ).status_code
        == 422
    )


def test_scheduler_deduplicates_persists_and_records_missed_alarms(client):
    now = datetime(2026, 11, 17, 16, 0, tzinfo=UTC)
    created = client.post(
        "/api/alarms", json={"data": alarm(recurrence_rule="FREQ=DAILY;COUNT=3"), "confirm": True}
    ).json()
    planning.tick(now)
    planning.tick(now)
    entries = store.all_records("alarm_occurrences")
    assert len(entries) == 1 and entries[0]["status"] == "pending"
    assert store.get("alarms", created["id"])["next_due_at"].startswith("2026-11-18T16:00")
    store.engine.dispose()
    store.initialize()
    planning.tick(now)
    assert len(store.all_records("alarm_occurrences")) == 1
    planning.tick(now + timedelta(days=1, hours=1))
    assert any(
        item["status"] == "missed" and item["delivery"] == "not_delivered"
        for item in store.all_records("alarm_occurrences")
    )


def test_alarm_claim_presentation_snooze_and_dismiss_are_not_replayed(client):
    created = client.post("/api/notifications/test", json={"confirm": True, "mode": "silent"})
    assert created.status_code == 200, created.text
    occurrence = client.get("/api/alarms/occurrences?active=true").json()[0]
    claim = client.post("/api/alarm-occurrences/" + occurrence["id"] + "/claim", json={}).json()
    assert (
        client.post("/api/alarm-occurrences/" + occurrence["id"] + "/claim", json={}).status_code
        == 409
    )
    ack = {
        "claim_token": claim["claim_token"],
        "notification_requested": False,
        "audio_started": False,
    }
    assert (
        client.post(
            "/api/alarm-occurrences/" + occurrence["id"] + "/presented", json=ack
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/alarm-occurrences/" + occurrence["id"] + "/presented", json=ack
        ).status_code
        == 409
    )
    result = client.post(
        "/api/alarm-occurrences/" + occurrence["id"] + "/snooze", json={"minutes": 5}
    )
    assert result.status_code == 200 and result.json()["status"] == "queued"
    assert (
        client.post(
            "/api/alarm-occurrences/" + occurrence["id"] + "/snooze", json={"minutes": 5}
        ).status_code
        == 409
    )
    planning.tick(instant(result.json()["scheduled_at"], "UTC"))
    assert store.get("alarm_occurrences", result.json()["id"])["status"] == "pending"
    assert (
        client.post(
            "/api/alarm-occurrences/" + result.json()["id"] + "/dismiss", json={}
        ).status_code
        == 200
    )


def test_alarm_agent_proposal_needs_approval_and_private_endpoints_stay_private(client):
    proposed = client.post("/api/tools/create_alarm", json={"arguments": alarm()}).json()
    assert proposed["approval_required"] and not store.all_records("alarms")
    assert (
        client.post("/api/approvals/" + proposed["approval_id"], json={"approve": True}).status_code
        == 200
    )
    assert store.all_records("alarms")[0]["scheduled_at"].startswith("2026-11-17T16:00")
    assert not client.get("/api/notifications/capabilities").json()["push_configurado"]
    client.cookies.clear()
    assert client.get("/api/alarms").status_code == 401
    assert client.get("/api/calendar/events").status_code == 401
    assert client.post("/api/notifications/test", json={"confirm": True}).status_code == 401


def test_alarm_state_survives_separate_process_restart_without_duplicate(tmp_path):
    environment = {
        **os.environ,
        "SALY_DATA_DIR": str(tmp_path),
        "SALY_DATABASE_URL": "sqlite:///" + str(tmp_path / "saly-v2.sqlite3"),
        "SALY_OWNER_PASSWORD_HASH": "",
    }
    create = """
from backend import storage as s
from backend.planning import save_alarm
s.initialize()
save_alarm({'title':'Reinício controlado','scheduled_at':'2026-11-17T13:00','timezone':'America/Sao_Paulo'})
"""
    tick = """
import json
from datetime import datetime,UTC
from backend import storage as s
from backend.planning import tick
s.initialize()
tick(datetime(2026,11,17,16,tzinfo=UTC))
print(json.dumps({'count':len(s.all_records('alarm_occurrences')),'status':s.all_records('alarm_occurrences')[0]['status']}))
"""
    subprocess.run([sys.executable, "-c", create], env=environment, capture_output=True, check=True)
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", tick],
            env=environment,
            capture_output=True,
            check=True,
            text=True,
        )
        assert json.loads(result.stdout) == {"count": 1, "status": "pending"}
