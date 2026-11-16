def test_feature_lab_executes_fixed_probes_without_external_calls_or_personal_records(client):
    from backend import storage as store
    from backend.main import provider

    result = client.post("/api/laboratory/features", json={})
    assert result.status_code == 200, result.text
    report = result.json()
    assert report["kind"] == "feature-lab-v1" and report["provider_requests"] == 0
    assert len(report["results"]) == 8
    assert not [c for c in report["results"] if c["status"] == "failed"]
    cases = {c["id"]: c for c in report["results"]}
    assert cases["F02"]["observed"]["total_cents"] == 25589
    assert cases["F03"]["observed"]["external_requests"] == 0
    assert cases["F04"]["observed"]["publication_status"] == "draft"
    assert (
        not store.all_records("purchases")
        and not store.all_records("alarms")
        and not store.all_records("private_assets")
    )
    assert len(client.get("/api/laboratory").json()) == 1
    assert client.get("/api/evaluation").json() == []
    assert not provider.key
    client.cookies.clear()
    assert client.post("/api/laboratory/features", json={}).status_code == 401


def test_device_reports_are_typed_authenticated_and_identified_as_browser_report(client):
    body = {
        "results": [
            {
                "id": "indexeddb",
                "category": "IndexedDB",
                "status": "passed",
                "duration_ms": 4,
                "detail": "Browser write/read test",
                "observed": {"writeRead": True},
            }
        ]
    }
    result = client.post("/api/laboratory/device", json=body)
    assert result.status_code == 200 and result.json()["kind"] == "device-lab-v1"
    assert "relatados pelo navegador" in result.json()["scope"]
    assert (
        client.post(
            "/api/laboratory/device",
            json={"results": [{**body["results"][0], "id": "fake-new-engine"}]},
        ).status_code
        == 422
    )
    client.cookies.clear()
    assert client.post("/api/laboratory/device", json=body).status_code == 401
