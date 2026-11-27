"""Database queries for orders, order items and order history."""
from typing import Optional

from ..database import utc_now

ORDER_SELECT = (
    "SELECT o.*, c.name AS customer_name, c.phone AS customer_phone, "
    "(SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.id) AS item_count "
    "FROM orders o LEFT JOIN customers c ON c.id = o.customer_id"
)


def order_to_dict(row) -> dict:
    d = dict(row)
    d["is_demo"] = bool(d["is_demo"])
    return d


def item_to_dict(row) -> dict:
    d = dict(row)
    d["needs_review"] = bool(d["needs_review"])
    return d


def get_order(conn, shop_id: int, order_id: int) -> Optional[dict]:
    row = conn.execute(
        f"{ORDER_SELECT} WHERE o.id = ? AND o.shop_id = ?", (order_id, shop_id)
    ).fetchone()
    return order_to_dict(row) if row else None


def find_by_idempotency_key(conn, shop_id: int, key: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM orders WHERE shop_id = ? AND idempotency_key = ?", (shop_id, key)
    ).fetchone()
    return row["id"] if row else None


def next_order_number(conn, shop_id: int, prefix: str, day: str) -> str:
    stem = f"{prefix}-{day}-"
    row = conn.execute(
        "SELECT order_number FROM orders WHERE shop_id = ? AND order_number LIKE ? "
        "ORDER BY order_number DESC LIMIT 1",
        (shop_id, stem + "%"),
    ).fetchone()
    last = int(row["order_number"].rsplit("-", 1)[1]) if row else 0
    return f"{stem}{last + 1:04d}"


def insert_order(conn, shop_id: int, values: dict) -> int:
    now = utc_now()
    cols = ["shop_id", *values.keys(), "created_at", "updated_at"]
    params = [shop_id, *values.values(), now, now]
    cur = conn.execute(
        f"INSERT INTO orders ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", params
    )
    return cur.lastrowid


def update_order(conn, order_id: int, values: dict) -> None:
    if not values:
        return
    assignments = ", ".join(f"{k} = ?" for k in values)
    conn.execute(
        f"UPDATE orders SET {assignments}, updated_at = ? WHERE id = ?",
        [*values.values(), utc_now(), order_id],
    )


def get_items(conn, order_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY position, id", (order_id,)
    )
    return [item_to_dict(r) for r in rows]


def replace_items(conn, order_id: int, items: list[dict]) -> None:
    conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    for pos, item in enumerate(items):
        conn.execute(
            "INSERT INTO order_items (order_id, position, product_id, product_name_spoken, "
            "product_name, quantity, unit, needs_review, review_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                order_id, pos, item.get("product_id"), item.get("product_name_spoken", ""),
                item["product_name"], item.get("quantity"), item.get("unit"),
                int(bool(item.get("needs_review"))), item.get("review_reason", ""),
            ),
        )


def clear_review_flags(conn, order_id: int) -> None:
    conn.execute(
        "UPDATE order_items SET needs_review = 0, review_reason = '' WHERE order_id = ?",
        (order_id,),
    )


def add_history(conn, order_id: int, field: str, old, new) -> None:
    conn.execute(
        "INSERT INTO order_history (order_id, changed_at, field, old_value, new_value) "
        "VALUES (?, ?, ?, ?, ?)",
        (order_id, utc_now(), field, None if old is None else str(old),
         None if new is None else str(new)),
    )


def get_history(conn, order_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT changed_at, field, old_value, new_value FROM order_history "
        "WHERE order_id = ? ORDER BY id",
        (order_id,),
    )
    return [dict(r) for r in rows]


def list_orders(conn, shop_id: int, *, q: str = "", statuses: Optional[list[str]] = None,
                created_from: Optional[str] = None, created_to: Optional[str] = None,
                customer_id: Optional[int] = None, product: str = "",
                limit: int = 200) -> list[dict]:
    sql = f"{ORDER_SELECT} WHERE o.shop_id = ?"
    params: list = [shop_id]
    if q:
        like = f"%{q}%"
        sql += (
            " AND (o.order_number LIKE ? OR c.name LIKE ? OR c.phone LIKE ? "
            "OR EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.id "
            "AND (i.product_name LIKE ? OR i.product_name_spoken LIKE ?)))"
        )
        params += [like] * 5
    if statuses:
        sql += f" AND o.status IN ({','.join('?' * len(statuses))})"
        params += statuses
    if created_from:
        sql += " AND o.created_at >= ?"
        params.append(created_from)
    if created_to:
        sql += " AND o.created_at < ?"
        params.append(created_to)
    if customer_id:
        sql += " AND o.customer_id = ?"
        params.append(customer_id)
    if product:
        sql += (
            " AND EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.id "
            "AND (i.product_name LIKE ? OR i.product_name_spoken LIKE ?))"
        )
        params += [f"%{product}%"] * 2
    sql += " ORDER BY o.created_at DESC, o.id DESC LIMIT ?"
    params.append(limit)
    return [order_to_dict(r) for r in conn.execute(sql, params)]


def recent_orders_for_customer(conn, shop_id: int, customer_id: int, since: str,
                               exclude_id: Optional[int]) -> list[dict]:
    rows = conn.execute(
        f"{ORDER_SELECT} WHERE o.shop_id = ? AND o.customer_id = ? AND o.created_at >= ? "
        "AND o.status != 'cancelled' AND o.id != ? ORDER BY o.created_at DESC",
        (shop_id, customer_id, since, exclude_id or -1),
    )
    return [order_to_dict(r) for r in rows]
