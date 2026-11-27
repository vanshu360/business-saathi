import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import make_settings

EXPECTED_TABLES = {
    "shops", "settings", "customers", "products", "product_aliases",
    "transcriptions", "orders", "order_items", "order_history",
}


def test_starts_without_api_key(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_status_reports_missing_key_clearly(client):
    body = client.get("/api/system/status").json()
    assert body["sarvam_configured"] is False
    assert "SARVAM_API_KEY" in body["sarvam_message"]
    assert "manual order entry works" in body["sarvam_message"]


def test_status_never_returns_the_key(tmp_path):
    secret = "sk_test_should_not_leak"
    with TestClient(create_app(make_settings(tmp_path, api_key=secret))) as c:
        res = c.get("/api/system/status")
    assert res.json()["sarvam_configured"] is True
    assert secret not in res.text


def test_database_tables_created(client, settings):
    conn = sqlite3.connect(settings.database_path)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= names
    assert conn.execute("SELECT name FROM shops WHERE id = 1").fetchone() == ("My Shop",)


def test_data_survives_app_restart(settings):
    create_app(settings)
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        "INSERT INTO customers (shop_id, name, created_at, updated_at) VALUES (1, 'Test', 'x', 'x')"
    )
    conn.commit()
    conn.close()
    create_app(settings)
    conn = sqlite3.connect(settings.database_path)
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 1


def test_frontend_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Business Saathi" in res.text
