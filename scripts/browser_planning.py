"""Calendar CRUD and actual UI alarm occurrence, with disposable persistent backend."""

import json
import os
from datetime import UTC, datetime, timedelta

from browser_support import PASSWORD, test_server
from playwright.sync_api import expect, sync_playwright

with test_server(port=8004) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1050})
    context.grant_permissions(["notifications"], origin=base)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""
    window.__notificationRequests=0;
    const Original=window.Notification;
    window.Notification=class extends Original{constructor(...args){super(...args);window.__notificationRequests++;}};
    """)
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.get_by_role("link", name="Agenda", exact=True).click()
    page.get_by_role("heading", name="Agenda inteligente", exact=True).wait_for()
    day = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
    page.get_by_label("Data de referência", exact=True).fill(day)
    page.get_by_role("button", name="+ Novo evento", exact=True).click()
    page.get_by_label("Título do evento", exact=True).fill("Estudo de Biologia E2E")
    page.get_by_label("Início do evento", exact=True).fill(day + "T13:00")
    page.get_by_label("Fim do evento", exact=True).fill(day + "T14:00")
    page.get_by_label("Repetição", exact=True).select_option("weekly")
    page.get_by_label("Associar alarme opcional", exact=True).check()
    page.get_by_role("button", name="Verificar prévia e conflitos", exact=True).click()
    page.get_by_role("region", name="Prévia do evento").wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Confirmar evento e alarme", exact=True).click()
    page.get_by_role("heading", name="Criar evento", exact=True).wait_for(state="hidden")
    events = context.request.get(base + "/api/calendar/events").json()
    assert len(events) == 1 and events[0]["alarm_id"]
    event = events[0]
    page.get_by_role("button", name="Estudo de Biologia E2E", exact=False).first.click()
    page.get_by_label("Título do evento", exact=True).fill("Biologia revisada E2E")
    page.get_by_role("button", name="Verificar prévia e conflitos", exact=True).click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Confirmar evento e alarme", exact=True).click()
    page.get_by_role("heading", name="Editar evento", exact=True).wait_for(state="hidden")
    assert (
        context.request.get(base + "/api/calendar/events").json()[0]["title"]
        == "Biologia revisada E2E"
    )
    page.get_by_label("Visualização da agenda", exact=True).select_option("day")
    page.get_by_role("button", name="Biologia revisada E2E", exact=False).first.wait_for()
    page.get_by_label("Visualização da agenda", exact=True).select_option("week")
    page.get_by_role("button", name="Biologia revisada E2E", exact=False).first.wait_for()
    page.get_by_label("Visualização da agenda", exact=True).select_option("month")
    page.get_by_role("button", name="Biologia revisada E2E", exact=False).first.wait_for()
    page.get_by_role("link", name="Alarmes", exact=True).click()
    page.get_by_role("heading", name="Alarmes", exact=True).wait_for()
    assert context.request.get(base + "/api/notifications/capabilities").json()[
        "scheduler_observed"
    ]["running"]
    page.get_by_role("button", name="+ Novo alarme", exact=True).click()
    page.get_by_label("Título do alarme", exact=True).fill("Lembrete independente E2E")
    page.get_by_label("Data e hora do alarme", exact=True).fill(day + "T09:00")
    page.get_by_label("Repetição", exact=True).select_option("daily")
    page.get_by_label("Modo do alarme", exact=True).select_option("silent")
    page.get_by_role("button", name="Verificar prévia do alarme", exact=True).click()
    page.get_by_role("region", name="Prévia do alarme").wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Confirmar alarme", exact=True).click()
    page.get_by_role("heading", name="Criar alarme", exact=True).wait_for(state="hidden")
    page.reload()
    page.get_by_role("heading", name="Lembrete independente E2E", exact=True).wait_for()
    page.get_by_label("Permitir avisos de alarmes e lembretes nesta interface", exact=True).check()
    expect(
        page.get_by_role("button", name="Testar apresentação de alarme", exact=True)
    ).to_be_enabled()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Testar apresentação de alarme", exact=True).click()
    notice = page.get_by_role("alert", name="Ocorrência de alarme")
    notice.get_by_text("Teste de alarme SALY", exact=True).wait_for()
    page.wait_for_function("window.__notificationRequests===1")
    occurrences = context.request.get(base + "/api/alarms/occurrences").json()
    assert len(occurrences) == 1
    assert occurrences[0]["delivery"] == "ui_reported" and occurrences[0]["notification_requested"]
    page.reload()
    notice.get_by_text("Teste de alarme SALY", exact=True).wait_for()
    assert (
        page.evaluate("window.__notificationRequests") == 0
    )  # Restore the notice, never replay the sound/OS request.
    notice.get_by_role("button", name="Adiar 5 min", exact=True).click()
    expect(notice).to_have_count(0)
    occurrences = context.request.get(base + "/api/alarms/occurrences").json()
    assert len(occurrences) == 2 and any(item["status"] == "queued" for item in occurrences)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Testar apresentação de alarme", exact=True).click()
    notice.get_by_text("Teste de alarme SALY", exact=True).wait_for()
    notice.get_by_role("button", name="Concluir aviso", exact=True).click()
    expect(notice).to_have_count(0)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.wait_for_function(
        "document.querySelector('.sidebar').getBoundingClientRect().right <= 0.5"
    )
    page.screenshot(path="/tmp/saly-alarms-mobile.png", full_page=True)
    # Deleting an event really cancels the linked alarm.
    result = context.request.delete(
        base + "/api/calendar/events/" + event["id"] + "?confirm=true",
        headers={"X-Saly-Request": "1"},
    )
    assert result.status == 200
    associated = next(
        item
        for item in context.request.get(base + "/api/alarms").json()
        if item["id"] == event["alarm_id"]
    )
    assert not associated["enabled"]
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "flows": [
                    "event preview/create/edit",
                    "day/week/month views",
                    "linked and independent recurring alarms",
                    "backend scheduler observed",
                    "real UI occurrence and native Notification API request",
                    "reload does not replay Notification",
                    "snooze/dismiss",
                    "event deletion cancels alarm",
                    "mobile",
                ],
                "provider_requests": 0,
                "page_errors": errors,
            }
        )
    )
    browser.close()
