"""Key/value shop settings."""

DEFAULTS = {
    "shop_name": "My Shop",
    "default_language": "unknown",
    "time_format": "12h",
}


def get_all(conn, shop_id: int) -> dict:
    values = dict(DEFAULTS)
    for row in conn.execute("SELECT key, value FROM settings WHERE shop_id = ?", (shop_id,)):
        if row["key"] in values:
            values[row["key"]] = row["value"]
    return values


def save(conn, shop_id: int, values: dict) -> None:
    for key, value in values.items():
        conn.execute(
            "INSERT INTO settings (shop_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(shop_id, key) DO UPDATE SET value = excluded.value",
            (shop_id, key, str(value)),
        )
