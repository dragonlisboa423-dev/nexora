import io
import shutil
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def real_voice(monkeypatch):
    system = shutil.which("espeak-ng")
    local = ROOT / ".tools/espeak/runtime"
    if system:
        monkeypatch.setenv("SALY_ESPEAK_BINARY", system)
    elif (local / "usr/bin/espeak-ng").is_file():
        monkeypatch.setenv("SALY_ESPEAK_BINARY", str(local / "usr/bin/espeak-ng"))
        monkeypatch.setenv("SALY_ESPEAK_DATA_PATH", str(local / "usr/lib/x86_64-linux-gnu/espeak-ng-data"))
        monkeypatch.setenv("SALY_ESPEAK_LIBRARY_PATH", str(local / "usr/lib/x86_64-linux-gnu"))
    else:
        pytest.skip("eSpeak NG not installed; real synthesis not certified")


def test_real_local_voice_produces_valid_nonempty_wav(client, real_voice):
    catalog = client.get("/api/voices").json()
    assert catalog["providers"][0]["available"]
    tool = client.post("/api/tools/list_voices", json={"arguments": {}})
    assert tool.status_code == 200 and tool.json()["executed"]
    assert tool.json()["result"]["providers"][0]["available"]
    result = client.post("/api/voices/preview", json={"text": "Olá. Esta é uma verificação real de áudio em português brasileiro."})
    assert result.status_code == 200, result.text[:100]
    assert result.headers["content-type"].startswith("audio/wav")
    assert result.headers["cache-control"] == "no-store"
    with wave.open(io.BytesIO(result.content), "rb") as audio:
        assert audio.getframerate() == 22050 and audio.getnchannels() == 1
        assert 0 < audio.getnframes() < 22050 * 30
        data = audio.readframes(audio.getnframes())
        assert any(data) and len(set(data)) > 30
    different = client.post("/api/voices/synthesize", json={"text": "Outra frase."})
    assert different.status_code == 200 and different.content != result.content
    assert client.get("/api/conversations").json() == []
    assert "verificação real" not in str(client.get("/api/activity").json())


def test_voice_configuration_and_authorization_fail_honestly(client, monkeypatch):
    monkeypatch.setenv("SALY_ESPEAK_BINARY", "/missing-tts-binary")
    assert not client.get("/api/voices").json()["providers"][0]["available"]
    response = client.post("/api/voices/preview", json={"text": "Teste"})
    assert response.status_code == 503 and "não instalado" in response.json()["detail"]
    assert client.post("/api/voices/preview", json={"text": "Teste", "voice_id": "../../etc/passwd"}).status_code == 422
    assert client.post("/api/voices/preview", json={"text": "Teste", "rate": 99}).status_code == 422
    client.cookies.clear()
    assert client.get("/api/voices").status_code == 401
    assert client.post("/api/voices/preview", json={"text": "Teste"}).status_code == 401
