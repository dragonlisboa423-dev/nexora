import io

from PIL import Image

from backend import storage as store


def purchase(**updates):
    return {
        "product": "Microscópio",
        "price_cents": 12345,
        "quantity": 2,
        "shipping_cents": 999,
        "discount_cents": 100,
        "purchased_on": "2026-11-16",
        **updates,
    }


def create(client, kind, data):
    result = client.post("/api/" + kind, json={"data": data, "confirm": True})
    assert result.status_code == 200, result.text
    return result.json()


def test_purchase_integer_totals_budget_status_and_revision(client):
    data = purchase(installments=3, category="ciência")
    preview = client.post("/api/purchases/preview", json=data)
    assert preview.json()["total_cents"] == 25589
    assert not store.all_records("purchases")
    assert client.post("/api/purchases", json={"data": data}).status_code == 400
    saved = create(client, "purchases", data)
    create(client, "purchases", purchase(status="wishlist", purchased_on=None))
    assert (
        client.put(
            "/api/purchases-budget",
            json={"month": "2026-11", "amount_cents": 30000, "confirm": True},
        ).status_code
        == 200
    )
    summary = client.get("/api/purchases-summary?month=2026-11").json()
    assert (
        summary["total_cents"] == 25589
        and summary["count"] == 1
        and summary["remaining_cents"] == 4411
    )
    assert summary["categories"] == {"ciência": 25589}
    assert (
        summary["installments"][0]["base_cents"] * 3 + summary["installments"][0]["remainder_cents"]
        == 25589
    )
    body = {
        "data": purchase(product="Lâminas"),
        "base_revision": saved["revision"],
        "confirm": True,
    }
    assert client.patch("/api/purchases/" + saved["id"], json=body).status_code == 200
    assert client.patch("/api/purchases/" + saved["id"], json=body).status_code == 409
    assert client.post("/api/purchases/preview", json=purchase(price_cents=1.5)).status_code == 422
    assert (
        client.post("/api/purchases/preview", json=purchase(discount_cents=99999999)).status_code
        == 422
    )


def test_receipt_is_real_private_normalized_replaceable_and_deleted(client):
    saved = create(client, "purchases", purchase())
    image = Image.new("RGB", (80, 50), "green")
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=b"SECRET-METADATA")
    raw = output.getvalue()
    result = client.post(
        f"/api/purchases/{saved['id']}/image?base_revision=1",
        headers={"X-Saly-Request": "1"},
        files={"file": ("receipt.jpg", raw, "image/jpeg")},
    )
    assert result.status_code == 200, result.text
    saved = result.json()
    asset = saved["image_id"]
    result = client.get("/api/private-assets/" + asset)
    assert "no-store" in result.headers["cache-control"]
    assert b"SECRET-METADATA" not in result.content
    assert Image.open(io.BytesIO(result.content)).size == (80, 50)
    assert (
        client.post(
            f"/api/purchases/{saved['id']}/image?base_revision=1",
            headers={"X-Saly-Request": "1"},
            files={"file": ("receipt.jpg", raw, "image/jpeg")},
        ).status_code
        == 409
    )
    assert len(store.all_records("private_assets")) == 1
    assert (
        client.post(
            f"/api/purchases/{saved['id']}/image?base_revision=2",
            headers={"X-Saly-Request": "1"},
            files={"file": ("evil.svg", b'<svg onload="alert(1)"/>', "image/svg+xml")},
        ).status_code
        == 422
    )
    assert (
        client.delete(
            f"/api/purchases/{saved['id']}?confirm=true&base_revision=2",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    assert client.get("/api/private-assets/" + asset).status_code == 404
    assert not store.all_records("private_assets")
    client.cookies.clear()
    assert client.get("/api/private-assets/" + asset).status_code == 401
    assert client.get("/api/purchases").status_code == 401


def test_purchase_alert_reuses_central_scheduler_and_cancels_on_delete(client):
    saved = create(client, "purchases", purchase(expected_on="2026-11-20"))
    result = client.post(
        "/api/purchases/" + saved["id"] + "/alarm",
        json={"field": "expected_on", "days_before": 1, "base_revision": 1, "confirm": True},
    )
    assert result.status_code == 200, result.text
    alarm = result.json()
    assert alarm["scheduled_at"].startswith("2026-11-19T12:00")
    assert (
        client.delete(
            f"/api/purchases/{saved['id']}?confirm=true&base_revision=2",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    assert not store.get("alarms", alarm["id"])["enabled"]


def test_links_safe_schemes_explicit_http_and_movement(client):
    a = create(client, "drawers", {"name": "Ciência"})
    b = create(client, "drawers", {"name": "Livros", "position": 1})
    for url in (
        "javascript:alert(1)",
        "data:text/html,<script>",
        "file:///etc/passwd",
        "https://u:p@example.org",
        "https://example.org\\evil",
        "https://example.org\n",
    ):
        assert (
            client.post(
                "/api/links/preview", json={"title": "x", "url": url, "drawer_id": a["id"]}
            ).status_code
            == 422
        )
    data = {"title": "Referência", "url": "http://example.org", "drawer_id": a["id"]}
    assert client.post("/api/links/preview", json=data).status_code == 422
    saved = create(client, "links", {**data, "allow_http": True})
    moved = client.patch(
        "/api/links/" + saved["id"],
        json={
            "data": {**data, "url": "https://example.org", "drawer_id": b["id"], "favorite": True},
            "base_revision": 1,
            "confirm": True,
        },
    )
    assert moved.status_code == 200 and moved.json()["favorite"]
    assert (
        client.delete(
            "/api/drawers/" + a["id"] + "?base_revision=1&confirm=true",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    assert store.get("links", saved["id"])
    assert (
        client.delete(
            "/api/drawers/" + b["id"] + "?base_revision=1&confirm=true",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    assert not store.get("links", saved["id"])


def test_space_export_import_is_additive_and_atomic(client):
    drawer = create(client, "drawers", {"name": "Leitura"})
    create(
        client,
        "links",
        {"title": "Exemplo", "url": "https://example.org", "drawer_id": drawer["id"]},
    )
    exported = client.get("/api/personal-export").json()
    body = {k: exported[k] for k in ("drawers", "links")}
    body.update(format="saly-space-v1", confirm=True)
    assert client.post("/api/space-import", json=body).status_code == 200
    assert len(store.all_records("drawers")) == 2 and len(store.all_records("links")) == 2
    body["links"][0]["url"] = "javascript:evil()"
    assert client.post("/api/space-import", json=body).status_code == 422
    assert len(store.all_records("drawers")) == 2 and len(store.all_records("links")) == 2


def test_optional_personal_sync_keeps_old_clients_private_and_cascades_tombstones(client):
    import uuid

    drawer = create(client, "drawers", {"name": "Cofre"})
    link = create(
        client,
        "links",
        {"title": "Exemplo", "url": "https://example.org", "drawer_id": drawer["id"]},
    )
    snapshot = client.get("/api/sync/bootstrap").json()
    assert set(snapshot["entities"]) == {"memories", "reminders", "documents"}
    assert not client.get("/api/sync/pull?after=0").json()["changes"]
    selected = client.get("/api/sync/bootstrap?kinds=purchases,drawers,links").json()
    assert selected["entities"]["drawers"][0]["id"] == drawer["id"]
    assert client.get("/api/sync/bootstrap?kinds=private_assets").status_code == 422
    operation = {
        "id": str(uuid.uuid4()),
        "entity_type": "purchases",
        "entity_id": store.uid(),
        "base_revision": 0,
        "payload": purchase(),
        "action": "upsert",
        "confirmed": True,
    }
    result = client.post("/api/sync/push", json={"operations": [operation]}).json()["results"][0]
    assert result["status"] == "applied" and result["record"]["total_cents"] == 25589
    assert client.post("/api/sync/push", json={"operations": [operation]}).json()["results"][0][
        "duplicate"
    ]
    deletion = {
        "id": str(uuid.uuid4()),
        "entity_type": "drawers",
        "entity_id": drawer["id"],
        "base_revision": 1,
        "action": "delete",
        "confirmed": True,
    }
    assert (
        client.post("/api/sync/push", json={"operations": [deletion]}).json()["results"][0][
            "status"
        ]
        == "applied"
    )
    changes = client.get(
        "/api/sync/pull?after=" + str(selected["cursor"]) + "&kinds=drawers,links,purchases"
    ).json()["changes"]
    assert any(c["entity_id"] == link["id"] and c["deleted"] for c in changes)
    assert any(c["entity_id"] == drawer["id"] and c["deleted"] for c in changes)
