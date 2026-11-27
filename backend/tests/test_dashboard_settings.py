from tests.test_orders import manual_order


def test_dashboard_counts_come_from_database(client):
    empty = client.get("/api/dashboard").json()
    assert empty["orders_today"] == {"total": 0, "demo": 0}
    assert empty["recent_orders"] == []
    assert empty["has_demo_data"] is False

    a = client.post("/api/orders", json=manual_order()).json()
    b = client.post("/api/orders", json=manual_order(customer_name="Sita")).json()
    client.post(f"/api/orders/{b['id']}/confirm")
    data = client.get("/api/dashboard").json()
    assert data["orders_today"]["total"] == 2
    assert data["drafts"]["total"] == 1
    assert data["pending"]["total"] == 1
    assert data["completed"]["total"] == 0
    assert data["customers"]["total"] == 2
    assert [o["id"] for o in data["pending_orders"]] == [b["id"]]
    assert {o["id"] for o in data["recent_orders"]} == {a["id"], b["id"]}


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json()
    assert s["shop_name"] == "My Shop"
    assert s["time_format"] == "12h"
    assert "SARVAM_API_KEY" not in s and "sarvam_api_key" not in s
    res = client.put("/api/settings", json={
        "shop_name": "Sharma Kirana", "default_language": "hi-IN", "time_format": "24h"})
    assert res.json()["shop_name"] == "Sharma Kirana"
    assert client.get("/api/settings").json()["default_language"] == "hi-IN"


def test_settings_validation(client):
    res = client.put("/api/settings", json={"shop_name": "X", "default_language": "xx-IN"})
    assert res.status_code == 422


def test_languages_list_is_honest(client):
    langs = client.get("/api/languages").json()
    assert len(langs) == 24
    assert langs[0]["code"] == "unknown"
    assert {l["status"] for l in langs} <= {"documented", "tested"}
    assert any(l["code"] == "brx-IN" and l["name"] == "Bodo" for l in langs)


def test_order_details_include_allowed_actions(client):
    order = client.post("/api/orders", json=manual_order()).json()
    assert order["can_confirm"] is True
    assert order["allowed_next_statuses"] == ["cancelled"]
