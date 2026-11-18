import io

from PIL import Image

from backend import storage as store


def png(color):
    buffer = io.BytesIO()
    Image.new("RGB", (80, 60), color).save(buffer, format="PNG")
    return buffer.getvalue()


def purchase(client):
    response = client.post(
        "/api/purchases",
        json={
            "data": {
                "product": "Livro de campo",
                "price_cents": 4590,
                "quantity": 1,
                "purchased_on": "2026-11-17",
                "category": "livros",
            },
            "confirm": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def upload(client, item, endpoint, color):
    response = client.post(
        f"/api/purchases/{item['id']}/{endpoint}?base_revision={item['revision']}",
        files={"file": ("photo.png", png(color), "image/png")},
        headers={"X-Saly-Request": "1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_product_photo_and_receipt_are_distinct_private_preserved_on_edit_and_cascade(client):
    item = purchase(client)
    item = upload(client, item, "image", "blue")
    receipt = item["image_id"]
    item = upload(client, item, "product-photo", "green")
    photo = item["product_image_id"]
    assert (
        receipt != photo
        and client.get("/api/private-assets/" + receipt).content
        != client.get("/api/private-assets/" + photo).content
    )
    assert store.get("private_assets", photo)["purpose"] == "product_photo"
    updated = client.patch(
        "/api/purchases/" + item["id"],
        json={
            "data": {
                "product": "Livro botânico",
                "price_cents": 4590,
                "purchased_on": "2026-11-17",
                "category": "livros",
            },
            "base_revision": item["revision"],
            "confirm": True,
        },
    ).json()
    assert updated["product_image_id"] == photo and updated["image_id"] == receipt
    exported = client.get("/api/personal-export").json()["purchases"][0]
    assert "product_image_id" not in exported and "image_id" not in exported
    assert (
        client.delete(
            f"/api/purchases/{item['id']}?base_revision={updated['revision']}&confirm=true",
            headers={"X-Saly-Request": "1"},
        ).status_code
        == 200
    )
    assert client.get("/api/private-assets/" + photo).status_code == 404
    assert client.get("/api/private-assets/" + receipt).status_code == 404


def test_product_photo_revision_validation_and_removal_do_not_touch_receipt(client):
    item = upload(client, purchase(client), "image", "blue")
    revision = item["revision"]
    item = upload(client, item, "product-photo", "green")
    stale = client.post(
        f"/api/purchases/{item['id']}/product-photo?base_revision={revision}",
        files={"file": ("x.png", png("red"), "image/png")},
        headers={"X-Saly-Request": "1"},
    )
    assert stale.status_code == 409
    invalid = client.post(
        f"/api/purchases/{item['id']}/product-photo?base_revision={item['revision']}",
        files={"file": ("fake.png", b"not image", "image/png")},
        headers={"X-Saly-Request": "1"},
    )
    assert invalid.status_code == 422
    url = f"/api/purchases/{item['id']}/product-photo?base_revision={item['revision']}"
    assert client.delete(url, headers={"X-Saly-Request": "1"}).status_code == 400
    assert client.delete(url + "&confirm=true", headers={"X-Saly-Request": "1"}).status_code == 200
    assert client.get("/api/private-assets/" + item["image_id"]).status_code == 200
    assert client.get("/api/private-assets/" + item["product_image_id"]).status_code == 404
    client.cookies.clear()
    assert client.get("/api/private-assets/" + item["image_id"]).status_code == 401


def test_savings_goals_require_manual_values_confirmation_revision_and_persist_without_changing_budget(
    client,
):
    purchase(client)
    body = {"title": "Biblioteca", "target_cents": 20000, "saved_cents": 3500, "confirm": True}
    assert client.post("/api/savings-goals", json={**body, "confirm": False}).status_code == 400
    assert client.post("/api/savings-goals", json={**body, "saved_cents": -1}).status_code == 422
    assert client.post("/api/savings-goals", json={**body, "target_cents": 10.2}).status_code == 422
    goal = client.post("/api/savings-goals", json=body).json()
    assert goal["revision"] == 1 and goal["saved_cents"] == 3500
    store.initialize()
    assert client.get("/api/savings-goals").json()[0]["id"] == goal["id"]
    url = "/api/savings-goals/" + goal["id"]
    assert client.put(url, json={**body, "base_revision": 0}).status_code == 409
    updated = client.put(url, json={**body, "saved_cents": 5000, "base_revision": 1}).json()
    assert updated["revision"] == 2 and updated["saved_cents"] == 5000
    summary = client.get("/api/purchases-summary?month=2026-11").json()
    assert (
        summary["total_cents"] == 4590
        and summary["budget_cents"] is None
        and summary["remaining_cents"] is None
    )
    assert client.get("/api/personal-export").json()["savings_goals"][0]["saved_cents"] == 5000
    assert (
        client.delete(
            url + "?base_revision=1&confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 409
    )
    assert (
        client.delete(url + "?base_revision=2", headers={"X-Saly-Request": "1"}).status_code == 400
    )
    assert (
        client.delete(
            url + "?base_revision=2&confirm=true", headers={"X-Saly-Request": "1"}
        ).status_code
        == 200
    )
    assert client.get("/api/savings-goals").json() == []
    client.cookies.clear()
    assert client.get("/api/savings-goals").status_code == 401
