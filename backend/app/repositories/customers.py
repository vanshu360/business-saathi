"""Database queries for customers."""
from typing import Optional

from ..database import utc_now


def _to_dict(row) -> dict:
    d = dict(row)
    d["is_demo"] = bool(d["is_demo"])
    return d


def list_customers(conn, shop_id: int, q: str = "") -> list[dict]:
    sql = (
        "SELECT c.*, (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) AS order_count "
        "FROM customers c WHERE c.shop_id = ?"
    )
    params: list = [shop_id]
    if q:
        sql += " AND (c.name LIKE ? OR c.phone LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY c.name COLLATE NOCASE"
    return [_to_dict(r) for r in conn.execute(sql, params)]


def get_customer(conn, shop_id: int, customer_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM customers WHERE id = ? AND shop_id = ?", (customer_id, shop_id)
    ).fetchone()
    return _to_dict(row) if row else None


def find_by_phone(conn, shop_id: int, phone: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM customers WHERE shop_id = ? AND phone = ?", (shop_id, phone)
    ).fetchone()
    return _to_dict(row) if row else None


def find_by_exact_name(conn, shop_id: int, name: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM customers WHERE shop_id = ? AND name = ? COLLATE NOCASE", (shop_id, name)
    ).fetchall()
    return [_to_dict(r) for r in rows]


def insert_customer(conn, shop_id: int, name: str, phone: Optional[str], notes: str = "",
                    is_demo: bool = False) -> int:
    now = utc_now()
    cur = conn.execute(
        "INSERT INTO customers (shop_id, name, phone, notes, is_demo, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (shop_id, name, phone, notes, int(is_demo), now, now),
    )
    return cur.lastrowid


def update_customer(conn, customer_id: int, name: str, phone: Optional[str], notes: str) -> None:
    conn.execute(
        "UPDATE customers SET name = ?, phone = ?, notes = ?, updated_at = ? WHERE id = ?",
        (name, phone, notes, utc_now(), customer_id),
    )
