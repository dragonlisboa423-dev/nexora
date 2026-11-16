import io
import shutil
import time

import pytest
from PIL import Image

from backend import media
from backend import storage as store


def upload_image(client, color="green"):
    image = Image.new("RGB", (160, 90), color)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    result = client.post(
        "/api/media/assets?kind=image",
        files={"file": ("image.png", stream.getvalue(), "image/png")},
        headers={"X-Saly-Request": "1"},
    )
    assert result.status_code == 200, result.text
    return result.json()


def wait_job(client, key):
    for _ in range(150):
        job = next(j for j in client.get("/api/media/jobs").json() if j["id"] == key)
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.1)
    pytest.fail("Tarefa não encerrou")


def test_media_unconfigured_generation_never_claims_success_or_uses_paid_fallback(client):
    caps = client.get("/api/media/capabilities").json()
    assert not caps["image_generation"]["configured"]
    assert caps["video_generation"]["status"] == "nao_configurada"
    assert (
        client.post("/api/media/images/generate", json={"prompt": "x", "confirm": True}).status_code
        == 503
    )
    assert client.post("/api/media/videos/generate", json={}).status_code == 503
    assert not store.all_records("media_jobs")
    client.cookies.clear()
    assert client.get("/api/media/jobs").status_code == 401
    assert client.get("/api/media/assets").status_code == 401


def test_real_local_crop_rotation_and_private_checksum(client):
    asset = upload_image(client)
    result = client.post(
        "/api/media/images/edit",
        json={"asset_id": asset["id"], "crop": [10, 10, 100, 60], "rotate": 90, "confirm": True},
    )
    assert result.status_code == 200, result.text
    output = result.json()
    raw = client.get("/api/private-assets/" + output["id"]).content
    assert Image.open(io.BytesIO(raw)).size == (50, 90)
    assert output["method"] == "local_crop_rotate"
    assert (
        client.post(
            "/api/media/images/edit",
            json={"asset_id": asset["id"], "crop": [0, 0, 99999, 99999], "confirm": True},
        ).status_code
        == 422
    )
    assert (
        client.delete(
            "/api/media/assets/" + output["id"] + "?confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert client.get("/api/private-assets/" + output["id"]).status_code == 404


@pytest.mark.skipif(
    not shutil.which("ffmpeg"), reason="FFmpeg nativo ausente; nenhuma montagem será simulada"
)
def test_real_ffmpeg_montage_captions_transitions_export_and_history(client, tmp_path):
    a = upload_image(client)
    b = upload_image(client, "blue")
    body = {
        "scenes": [
            {"asset_id": a["id"], "duration": 1, "caption": "Legenda real 100%: vida"},
            {"asset_id": b["id"], "duration": 1},
        ],
        "transition": "fade",
        "confirm": True,
    }
    created = client.post("/api/media/montage", json=body)
    assert created.status_code == 200, created.text
    job = wait_job(client, created.json()["id"])
    assert job["status"] == "completed", job
    assert job["progress"]["encoded_seconds"] > 0 and job["result_sha256"]
    output = client.get("/api/private-assets/" + job["output_asset_ids"][0])
    assert output.headers["content-type"] == "video/mp4"
    path = tmp_path / "verified.mp4"
    path.write_bytes(output.content)
    info = media.probe(path)
    assert abs(info["duration"] - 2) < 0.1
    assert info["streams"][0]["width"] == 640 and info["streams"][0]["height"] == 360
    store.engine.dispose()
    store.initialize()
    assert client.get("/api/media/jobs").json()[0]["status"] == "completed"
    assert (
        client.delete(
            "/api/media/jobs/" + job["id"] + "?confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert client.get("/api/private-assets/" + job["output_asset_ids"][0]).status_code == 404


def test_cancelled_queue_does_not_render_and_restart_does_not_repeat_remote(client):
    job = media.new_job("image_generation", {"prompt": "x", "steps": 4}, [], "cloudflare")
    # No task is started: exercise persistent queued cancellation deterministically.
    assert (
        client.post("/api/media/jobs/" + job["id"] + "/cancel", json={}).json()["status"]
        == "cancelled"
    )
    assert client.post("/api/media/jobs/" + job["id"] + "/cancel", json={}).status_code == 409
    assert not store.get("media_jobs", job["id"])["output_asset_ids"]


def test_invalid_av_upload_and_unconfirmed_montage_are_rejected(client):
    bad = client.post(
        "/api/media/assets?kind=video",
        files={"file": ("fake.mp4", b"not a movie", "video/mp4")},
        headers={"X-Saly-Request": "1"},
    )
    assert bad.status_code == 422
    asset = upload_image(client)
    assert (
        client.post("/api/media/montage", json={"scenes": [{"asset_id": asset["id"]}]}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/media/montage",
            json={"scenes": [{"asset_id": asset["id"], "duration": 15}] * 5, "confirm": True},
        ).status_code
        == 422
    )


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg real ausente")
def test_real_clip_audio_normalization_and_two_tracks(client, tmp_path):
    import math
    import struct
    import wave

    image = upload_image(client)
    first = client.post(
        "/api/media/montage",
        json={"scenes": [{"asset_id": image["id"], "duration": 1}], "confirm": True},
    ).json()
    rendered = wait_job(client, first["id"])
    assert rendered["status"] == "completed", rendered
    clip_raw = client.get("/api/private-assets/" + rendered["output_asset_ids"][0]).content
    clip = client.post(
        "/api/media/assets?kind=video",
        files={"file": ("clip.mp4", clip_raw, "video/mp4")},
        headers={"X-Saly-Request": "1"},
    )
    assert clip.status_code == 200, clip.text
    stream = io.BytesIO()
    with wave.open(stream, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(22050)
        writer.writeframes(
            b"".join(
                struct.pack("<h", int(5000 * math.sin(2 * math.pi * 440 * i / 22050)))
                for i in range(11025)
            )
        )
    track = client.post(
        "/api/media/assets?kind=audio",
        files={"file": ("tone.wav", stream.getvalue(), "audio/wav")},
        headers={"X-Saly-Request": "1"},
    )
    assert track.status_code == 200, track.text
    track = track.json()
    result = client.post(
        "/api/media/montage",
        json={
            "scenes": [{"asset_id": clip.json()["id"], "duration": 0.75, "trim_start": 0.1}],
            "narration_asset_id": track["id"],
            "music_asset_id": track["id"],
            "orientation": "portrait",
            "confirm": True,
        },
    )
    assert result.status_code == 200, result.text
    job = wait_job(client, result.json()["id"])
    assert job["status"] == "completed", job
    raw = client.get("/api/private-assets/" + job["output_asset_ids"][0]).content
    path = tmp_path / "with-audio.mp4"
    path.write_bytes(raw)
    info = media.probe(path)
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert any(s.get("width") == 360 and s.get("height") == 640 for s in info["streams"])


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="Cancelamento exige FFmpeg real")
def test_running_ffmpeg_cancellation_removes_partial_outputs(client):
    image = upload_image(client)
    result = client.post(
        "/api/media/montage",
        json={
            "scenes": [{"asset_id": image["id"], "duration": 7} for _ in range(8)],
            "confirm": True,
        },
    )
    key = result.json()["id"]
    for _ in range(150):
        job = store.get("media_jobs", key)
        if job["status"] == "running" and job.get("progress"):
            break
        time.sleep(0.02)
    assert job["status"] == "running", job
    assert client.post("/api/media/jobs/" + key + "/cancel", json={}).status_code == 200
    job = wait_job(client, key)
    assert job["status"] == "cancelled" and not job["output_asset_ids"]
    assert not any(a.get("job_id") == key for a in store.all_records("private_assets"))


def test_cloudflare_contract_and_daily_guard_with_controlled_transport_only(client, monkeypatch):
    import asyncio
    import base64

    import httpx

    from backend.media_providers import CloudflareImageProvider

    monkeypatch.setenv("SALY_CF_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("SALY_CF_API_TOKEN", "disposable-test-token")
    monkeypatch.setenv("SALY_CF_WORKERS_FREE_CONFIRMED", "1")
    monkeypatch.setenv("SALY_CF_TERMS_REVIEWED", "1")
    stream = io.BytesIO()
    Image.new("RGB", (20, 20), "green").save(stream, format="PNG")
    calls = []

    def handler(request):
        import json

        calls.append(request)
        assert (
            str(request.url)
            == "https://api.cloudflare.com/client/v4/accounts/"
            + "a" * 32
            + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
        )
        assert json.loads(request.content) == {"prompt": "texto de teste", "steps": 4}
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {"image": base64.b64encode(stream.getvalue()).decode()},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **options: original(transport=httpx.MockTransport(handler), **options),
    )
    provider = CloudflareImageProvider()
    assert asyncio.run(provider.generate("texto de teste")) == stream.getvalue()
    with pytest.raises(ValueError, match="uma requisição"):
        asyncio.run(provider.generate("segundo teste"))
    assert len(calls) == 1
