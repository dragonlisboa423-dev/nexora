"""Real server WAV, browser decoding/playback and PCM-driven nucleus. No LLM call."""

import io
import json
import os
import shutil
import wave
from pathlib import Path

from browser_support import PASSWORD, ROOT, test_server
from playwright.sync_api import expect, sync_playwright

environment = {}
if not shutil.which("espeak-ng"):
    runtime = ROOT / ".tools/espeak/runtime"
    if not (runtime / "usr/bin/espeak-ng").is_file():
        raise RuntimeError(
            "eSpeak NG não instalado; teste real de voz não pode ser declarado aprovado"
        )
    environment = {
        "SALY_ESPEAK_BINARY": str(runtime / "usr/bin/espeak-ng"),
        "SALY_ESPEAK_DATA_PATH": str(runtime / "usr/lib/x86_64-linux-gnu/espeak-ng-data"),
        "SALY_ESPEAK_LIBRARY_PATH": str(runtime / "usr/lib/x86_64-linux-gnu"),
    }

with test_server(extra_environment=environment) as base, sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("SALY_CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox", "--enable-unsafe-swiftshader"],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1050})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""
    window.__salyAudioContexts=[];
    const AudioContextOriginal=window.AudioContext;
    window.AudioContext=class extends AudioContextOriginal {constructor(...args){super(...args);window.__salyAudioContexts.push(this);}};
    """)
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.get_by_role("heading", name="Olá. Eu sou Saly.").wait_for()
    page.goto(base + "/voices")
    catalog = page.get_by_role("region", name="Catálogo de vozes independentes")
    catalog.get_by_role("heading", name="Português BR · variante feminina f3").wait_for()
    catalog.get_by_label("Frase para prévia").fill(
        "Olá. Sou Saly. Esta é uma verificação real da síntese local em português brasileiro. Vamos testar pausa, continuação e parada sem utilizar as vozes do navegador."
    )
    catalog.get_by_role("button", name="Ouvir prévia local", exact=True).click()
    catalog.get_by_role("status").filter(has_text="reproduzindo").wait_for()
    page.wait_for_function(
        "window.__salyAudioContexts.some(audio=>audio.state==='running'&&audio.currentTime>0)"
    )
    catalog.get_by_role("button", name="Pausar áudio", exact=True).click()
    catalog.get_by_role("status").filter(has_text="pausado").wait_for()
    assert page.evaluate("window.__salyAudioContexts.at(-1).state") == "suspended"
    catalog.get_by_role("button", name="Continuar áudio", exact=True).click()
    catalog.get_by_role("status").filter(has_text="reproduzindo").wait_for()
    catalog.get_by_role("button", name="Parar áudio", exact=True).click()
    catalog.get_by_role("status").filter(has_text="sem reprodução ativa").wait_for()
    catalog.get_by_role("button", name="Selecionar voz local", exact=True).click()
    expect(catalog.get_by_role("button", name="Voz selecionada", exact=True)).to_be_visible()
    page.reload()
    catalog.get_by_role("button", name="Voz selecionada", exact=True).wait_for()
    with page.expect_download() as download:
        catalog.get_by_role("button", name="Baixar WAV da frase", exact=True).click()
    audio_bytes = Path(download.value.path()).read_bytes()
    Path("/tmp/saly-local-tts-preview.wav").write_bytes(audio_bytes)
    with wave.open(io.BytesIO(audio_bytes), "rb") as audio:
        assert audio.getnframes() > 0 and audio.getframerate() == 22050
    # Controlled language transport only; speech below still comes from the real local engine.
    text = "Esta resposta de teste existe somente para verificar o botão Ouvir, a síntese real e a reação do núcleo ao sinal PCM. Não foi gerada por um modelo remoto. Vamos continuar a verificação por alguns segundos para testar a pausa e o encerramento."
    page.route(
        "**/api/health",
        lambda route: route.fulfill(json={"model_ready": True, "model": "controlled-ui-transport"}),
    )
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(
            content_type="application/x-ndjson",
            body="".join(
                json.dumps(event) + "\n"
                for event in [
                    {
                        "type": "context",
                        "conversation_id": "voice-ui-test",
                        "sources": [],
                        "memory_ids": [],
                    },
                    {"type": "token", "text": text},
                    {"type": "done", "content": text},
                ]
            ),
        ),
    )
    page.goto(base)
    page.get_by_label("Mensagem para Saly").fill("Teste de reprodução local")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Enviar mensagem", exact=True).click()
    page.get_by_role("button", name="Ouvir", exact=True).click()
    page.locator('.core.speaking[data-speech-signal="pcm"]').wait_for()
    page.wait_for_function(
        "parseFloat(document.querySelector('.core').style.getPropertyValue('--audio-energy'))>0.01"
    )
    page.screenshot(path="/tmp/saly-voice-core.png", full_page=True)
    page.get_by_role("button", name="Pausar", exact=True).click()
    page.locator(".core.paused").wait_for()
    page.wait_for_function(
        "parseFloat(document.querySelector('.core').style.getPropertyValue('--audio-energy'))===0"
    )
    expect(page.locator(".speech-waves")).to_have_count(0)
    page.get_by_role("button", name="Retomar", exact=True).click()
    page.locator(".core.speaking").wait_for()
    page.get_by_role("button", name="Interromper", exact=True).click()
    page.wait_for_function("document.querySelector('.core').dataset.speechSignal==='events'")
    expect(page.locator(".speech-waves")).to_have_count(0)
    assert not errors, errors
    print(
        json.dumps(
            {
                "browser": "Chromium",
                "speech": "real eSpeak NG pt-br+f3 PCM",
                "wav_bytes": len(audio_bytes),
                "flows": [
                    "real WAV download",
                    "AudioContext playback/pause/resume/stop",
                    "voice selection persistence",
                    "PCM amplitude drives nucleus",
                    "no waveform in pause/stop",
                ],
                "llm_requests": 0,
                "page_errors": errors,
            }
        )
    )
    browser.close()
