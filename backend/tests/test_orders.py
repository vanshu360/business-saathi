import sqlite3
import uuid

import pytest


def new_key() -> str:
    return uuid.uuid4().hex


def manual_order(**overrides) -> dict:
    body = {
        "idempotency_key": new_key(),
        "customer_name": "Ramesh Kumar",
        "delivery_time_text": "evening",
        "items": [
            {"product_name": "Rice", "quantity": 2, "unit": "kg"},
            {"product_name": "Sugar", "quantity": 1, "unit": "kg"},
            {"product_name": "Cooking oil", "quantity": 2, "unit": "l"},
        ],
    }
    body.update(overrides)
    return body


def test_manual_order_created_as_draft_and_saved_in_sqlite(client, settings):
    res = client.post("/api/orders", json=manual_order())
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "draft"
    assert order["source"] == "manual"
    assert order["order_number"].startswith("BS-")
    assert order["customer_name"] == "Ramesh Kumar"
    assert [i["product_name"] for i in order["items"]] == ["Rice", "Sugar", "Cooking oil"]

    conn = sqlite3.connect(settings.database_path)
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 3


def test_saved_order_can_be_retrieved(client):
    oid = client.post("/api/orders", json=manual_order()).json()["id"]
    order = client.get(f"/api/orders/{oid}").json()
    assert order["delivery_time_text"] == "evening"
    assert order["history"][0]["field"] == "created"
    assert len(client.get("/api/orders").json()) == 1


def test_same_idempotency_key_creates_only_one_order(client):
    body = manual_order(status="confirmed")
    first = client.post("/api/orders", json=body)
    second = client.post("/api/orders", json=body)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["already_saved"] is True
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/api/orders").json()) == 1


def test_existing_customer_reused_not_duplicated(client):
    client.post("/api/orders", json=manual_order())
    client.post("/api/orders", json=manual_order(customer_name="ramesh kumar"))
    assert len(client.get("/api/customers").json()) == 1


def test_customer_matched_by_phone(client):
    cid = client.post("/api/customers", json={"name": "Ramesh", "phone": "9876543210"}).json()["id"]
    order = client.post("/api/orders", json=manual_order(
        customer_name=None, customer_phone="9876543210")).json()
    assert order["customer_id"] == cid


def test_order_without_customer_or_delivery_allowed(client):
    res = client.post("/api/orders", json=manual_order(customer_name=None, delivery_time_text=""))
    assert res.status_code == 201
    assert res.json()["customer_id"] is None
    assert res.json()["delivery_date"] is None


def test_confirm_requires_quantity_and_unit(client):
    order = client.post("/api/orders", json=manual_order(items=[
        {"product_name": "Biscuits", "needs_review": True, "review_reason": "quantity unclear"},
    ])).json()
    assert order["items"][0]["needs_review"] is True
    res = client.post(f"/api/orders/{order['id']}/confirm")
    assert res.status_code == 400
    assert "Biscuits" in res.json()["detail"]
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "draft"


def test_confirm_and_status_flow(client):
    oid = client.post("/api/orders", json=manual_order()).json()["id"]
    assert client.post(f"/api/orders/{oid}/confirm").json()["status"] == "confirmed"
    assert client.post(f"/api/orders/{oid}/confirm").status_code == 200
    for status in ("pending", "processing", "completed"):
        res = client.patch(f"/api/orders/{oid}/status", json={"status": status})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == status
    history = [h for h in client.get(f"/api/orders/{oid}").json()["history"] if h["field"] == "status"]
    assert [h["new_value"] for h in history] == ["confirmed", "pending", "processing", "completed"]


@pytest.mark.parametrize("start,target", [
    ("draft", "completed"), ("draft", "confirmed"), ("completed", "pending"),
])
def test_invalid_status_moves_rejected(client, start, target):
    oid = client.post("/api/orders", json=manual_order()).json()["id"]
    if start == "completed":
        client.post(f"/api/orders/{oid}/confirm")
        client.patch(f"/api/orders/{oid}/status", json={"status": "completed"})
    res = client.patch(f"/api/orders/{oid}/status", json={"status": target})
    assert res.status_code == 400


def test_cancel_and_cancelled_cannot_be_edited(client):
    oid = client.post("/api/orders", json=manual_order()).json()["id"]
    assert client.post(f"/api/orders/{oid}/cancel").json()["status"] == "cancelled"
    res = client.put(f"/api/orders/{oid}", json=manual_order())
    assert res.status_code == 400


def test_edit_order_records_history(client):
    oid = client.post("/api/orders", json=manual_order()).json()["id"]
    edited = manual_order(
        delivery_date="2026-11-28", delivery_time="18:30", special_instructions="Ring bell",
        items=[{"product_name": "Rice", "quantity": 5, "unit": "kg"}],
    )
    order = client.put(f"/api/orders/{oid}", json=edited).json()
    assert order["delivery_date"] == "2026-11-28"
    assert order["delivery_time"] == "18:30"
    assert [(i["product_name"], i["quantity"]) for i in order["items"]] == [("Rice", 5)]
    fields = {h["field"] for h in order["history"]}
    assert {"delivery_date", "delivery_time", "special_instructions", "items"} <= fields


def test_invalid_order_input_rejected(client):
    assert client.post("/api/orders", json=manual_order(idempotency_key="x")).status_code == 422
    bad_qty = manual_order(items=[{"product_name": "Rice", "quantity": -1, "unit": "kg"}])
    assert client.post("/api/orders", json=bad_qty).status_code == 422
    bad_time = manual_order(delivery_time="6pm")
    assert client.post("/api/orders", json=bad_time).status_code == 422


def test_search_and_filters(client):
    a = client.post("/api/orders", json=manual_order()).json()
    b = client.post("/api/orders", json=manual_order(
        customer_name="Sita Devi", items=[{"product_name": "Biscuits", "quantity": 4, "unit": "packet"}],
    )).json()
    client.post(f"/api/orders/{b['id']}/confirm")

    def numbers(query):
        return {o["order_number"] for o in client.get(f"/api/orders{query}").json()}

    assert numbers("?q=sita") == {b["order_number"]}
    assert numbers("?q=rice") == {a["order_number"]}
    assert numbers("?product=biscuit") == {b["order_number"]}
    assert numbers("?status=draft") == {a["order_number"]}
    assert numbers("?status=draft,confirmed") == {a["order_number"], b["order_number"]}
    assert numbers("?date_from=2000-01-01&date_to=2000-01-02") == set()
    assert client.get("/api/orders?status=bogus").status_code == 400


def test_possible_duplicate_detected(client):
    first = client.post("/api/orders", json=manual_order()).json()
    second = client.post("/api/orders", json=manual_order()).json()
    dups = client.get(f"/api/orders/{second['id']}/possible-duplicates").json()
    assert [d["id"] for d in dups] == [first["id"]]
    res = client.post("/api/orders/check-duplicates", json={
        "customer_id": first["customer_id"], "product_names": ["Tea"]})
    assert res.json() == []


def test_order_numbers_increment(client):
    n1 = client.post("/api/orders", json=manual_order()).json()["order_number"]
    n2 = client.post("/api/orders", json=manual_order()).json()["order_number"]
    assert int(n2.rsplit("-", 1)[1]) == int(n1.rsplit("-", 1)[1]) + 1


def test_correcting_customer_name_with_same_phone_is_saved(client):
    oid = client.post("/api/orders", json=manual_order(customer_name="Ramesh", customer_phone="9876543210")).json()["id"]
    order = client.put(f"/api/orders/{oid}", json=manual_order(customer_name="Ramesh Kumar", customer_phone="9876543210")).json()
    assert order["customer_name"] == "Ramesh Kumar"
