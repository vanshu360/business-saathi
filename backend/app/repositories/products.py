"""Database queries for products and their aliases."""
import sqlite3
from typing import Optional

from ..database import utc_now


def _with_aliases(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict]:
    products = [dict(r) for r in rows]
    if not products:
        return products
    ids = [p["id"] for p in products]
    marks = ",".join("?" * len(ids))
    aliases: dict[int, list[dict]] = {i: [] for i in ids}
    for a in conn.execute(
        f"SELECT id, product_id, alias, language_code FROM product_aliases "
        f"WHERE product_id IN ({marks}) ORDER BY alias",
        ids,
    ):
        aliases[a["product_id"]].append(dict(a))
    for p in products:
        p["aliases"] = aliases[p["id"]]
        p["is_active"] = bool(p["is_active"])
        p["is_demo"] = bool(p["is_demo"])
    return products


def list_products(conn, shop_id: int, q: str = "", include_inactive: bool = False) -> list[dict]:
    sql = "SELECT * FROM products p WHERE p.shop_id = ?"
    params: list = [shop_id]
    if not include_inactive:
        sql += " AND p.is_active = 1"
    if q:
        sql += (
            " AND (p.name LIKE ? OR EXISTS (SELECT 1 FROM product_aliases a "
            "WHERE a.product_id = p.id AND a.alias LIKE ?))"
        )
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY p.name COLLATE NOCASE"
    return _with_aliases(conn, conn.execute(sql, params).fetchall())


def get_product(conn, shop_id: int, product_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM products WHERE id = ? AND shop_id = ?", (product_id, shop_id)
    ).fetchone()
    return _with_aliases(conn, [row])[0] if row else None


def find_by_name(conn, shop_id: int, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM products WHERE shop_id = ? AND name = ? COLLATE NOCASE", (shop_id, name)
    ).fetchone()


def insert_product(conn, shop_id: int, name: str, unit: str, price, is_demo: bool = False) -> int:
    now = utc_now()
    cur = conn.execute(
        "INSERT INTO products (shop_id, name, default_unit, price, is_demo, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (shop_id, name, unit, price, int(is_demo), now, now),
    )
    return cur.lastrowid


def update_product(conn, product_id: int, name: str, unit: str, price, is_active: bool = True) -> None:
    conn.execute(
        "UPDATE products SET name = ?, default_unit = ?, price = ?, is_active = ?, updated_at = ? "
        "WHERE id = ?",
        (name, unit, price, int(is_active), utc_now(), product_id),
    )


def deactivate_product(conn, product_id: int) -> None:
    conn.execute(
        "UPDATE products SET is_active = 0, updated_at = ? WHERE id = ?", (utc_now(), product_id)
    )


def replace_aliases(conn, product_id: int, aliases: list[str]) -> None:
    conn.execute("DELETE FROM product_aliases WHERE product_id = ?", (product_id,))
    for alias in aliases:
        add_alias(conn, product_id, alias, None)


def add_alias(conn, product_id: int, alias: str, language_code: Optional[str]) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO product_aliases (product_id, alias, language_code) VALUES (?, ?, ?)",
        (product_id, alias, language_code),
    )


def delete_alias(conn, product_id: int, alias_id: int) -> int:
    cur = conn.execute(
        "DELETE FROM product_aliases WHERE id = ? AND product_id = ?", (alias_id, product_id)
    )
    return cur.rowcount
