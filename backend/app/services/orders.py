"""Order rules: creating, editing, confirming, status changes and duplicate checks."""
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import Settings
from ..errors import Conflict, InvalidRequest, NotFound
from ..repositories import customers as customers_repo
from ..repositories import orders as orders_repo
from ..schemas import OrderCreate, OrderFields
from ..timeutils import shop_today

# Which status can move to which. "confirmed" is only reachable via confirm_order().
ALLOWED_MOVES = {
    "draft": {"cancelled"},
    "confirmed": {"pending", "processing", "completed", "cancelled"},
    "pending": {"processing", "completed", "cancelled"},
    "processing": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
EDITABLE = {"draft", "confirmed", "pending", "processing"}
DUPLICATE_WINDOW = timedelta(hours=24)


def resolve_customer(conn: sqlite3.Connection, shop_id: int, data: OrderFields,
                     is_demo: bool = False) -> Optional[int]:
    """Finds the customer for an order, creating one only when no match exists."""
    if data.customer_id:
        if not customers_repo.get_customer(conn, shop_id, data.customer_id):
            raise NotFound("Customer not found")
        return data.customer_id
    if data.customer_phone:
        existing = customers_repo.find_by_phone(conn, shop_id, data.customer_phone)
        if existing:
            if data.customer_name and data.customer_name.strip() != existing["name"]:
                customers_repo.update_customer(conn, existing["id"], data.customer_name.strip(),
                                               existing["phone"], existing.get("notes") or "")
            return existing["id"]
        if not data.customer_name:
            raise InvalidRequest("Please enter the customer's name for this new phone number")
        return customers_repo.insert_customer(
            conn, shop_id, data.customer_name, data.customer_phone, is_demo=is_demo
        )
    if data.customer_name:
        matches = customers_repo.find_by_exact_name(conn, shop_id, data.customer_name)
        if len(matches) == 1:
            return matches[0]["id"]
        if len(matches) > 1:
            raise InvalidRequest(
                f"More than one customer is named '{data.customer_name}'. "
                "Please choose the customer from the list or add a phone number."
            )
        return customers_repo.insert_customer(conn, shop_id, data.customer_name, None,
                                              is_demo=is_demo)
    return None


def check_confirmable(items: list[dict]) -> None:
    if not items:
        raise InvalidRequest("Add at least one product before confirming the order")
    missing = [
        i.get("product_name") or f"item {n + 1}"
        for n, i in enumerate(items)
        if i.get("quantity") is None or not i.get("unit")
    ]
    if missing:
        raise InvalidRequest(
            "Quantity and unit are needed before confirming: " + ", ".join(missing)
        )


def get_order_details(conn, shop_id: int, order_id: int) -> dict:
    order = orders_repo.get_order(conn, shop_id, order_id)
    if not order:
        raise NotFound("Order not found")
    order["items"] = orders_repo.get_items(conn, order_id)
    order["history"] = orders_repo.get_history(conn, order_id)
    order["allowed_next_statuses"] = sorted(ALLOWED_MOVES[order["status"]])
    order["can_confirm"] = order["status"] == "draft"
    order["can_edit"] = order["status"] in EDITABLE
    order["transcription"] = None
    if order["transcription_id"]:
        row = conn.execute(
            "SELECT id, language_requested, language_detected, original_text, roman_text, "
            "english_text, original_status, roman_status, english_status "
            "FROM transcriptions WHERE id = ?",
            (order["transcription_id"],),
        ).fetchone()
        order["transcription"] = dict(row) if row else None
    return order


def _items_as_dicts(data: OrderFields) -> list[dict]:
    return [item.model_dump() for item in data.items]


def _summarise_items(items: list[dict]) -> str:
    parts = []
    for i in items:
        qty = "" if i.get("quantity") is None else f"{i['quantity']:g} "
        parts.append(f"{i['product_name']} {qty}{i.get('unit') or ''}".strip())
    return "; ".join(parts)


def create_order(conn, settings: Settings, shop_id: int, data: OrderCreate,
                 is_demo: bool = False) -> tuple[dict, bool]:
    """Returns (order, created). A repeated idempotency_key returns the first order unchanged."""
    existing_id = orders_repo.find_by_idempotency_key(conn, shop_id, data.idempotency_key)
    if existing_id:
        return get_order_details(conn, shop_id, existing_id), False

    items = _items_as_dicts(data)
    if data.status == "confirmed":
        check_confirmable(items)
    if data.transcription_id is not None:
        found = conn.execute(
            "SELECT 1 FROM transcriptions WHERE id = ? AND shop_id = ?",
            (data.transcription_id, shop_id),
        ).fetchone()
        if not found:
            raise NotFound("Transcription not found")

    customer_id = resolve_customer(conn, shop_id, data, is_demo=is_demo)
    prefix = "DEMO" if is_demo else "BS"
    number = orders_repo.next_order_number(
        conn, shop_id, prefix, shop_today(settings.timezone).strftime("%Y%m%d")
    )
    now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        order_id = orders_repo.insert_order(conn, shop_id, {
            "order_number": number,
            "customer_id": customer_id,
            "status": data.status,
            "source": data.source,
            "delivery_date": data.delivery_date.isoformat() if data.delivery_date else None,
            "delivery_time": data.delivery_time,
            "delivery_time_text": data.delivery_time_text,
            "special_instructions": data.special_instructions,
            "transcription_id": data.transcription_id,
            "idempotency_key": data.idempotency_key,
            "is_demo": int(is_demo),
            "confirmed_at": now_utc if data.status == "confirmed" else None,
        })
    except sqlite3.IntegrityError as exc:
        raise Conflict("This order was already saved. Please refresh the page.") from exc
    if data.status == "confirmed":
        for item in items:
            item["needs_review"] = False
            item["review_reason"] = ""
    orders_repo.replace_items(conn, order_id, items)
    orders_repo.add_history(conn, order_id, "created", None, data.status)
    return get_order_details(conn, shop_id, order_id), True


def update_order(conn, shop_id: int, order_id: int, data: OrderFields) -> dict:
    order = get_order_details(conn, shop_id, order_id)
    if order["status"] not in EDITABLE:
        raise InvalidRequest(f"A {order['status']} order cannot be edited")
    items = _items_as_dicts(data)
    if order["status"] != "draft":
        check_confirmable(items)
        for item in items:
            item["needs_review"] = False
            item["review_reason"] = ""

    customer_id = resolve_customer(conn, shop_id, data, is_demo=order["is_demo"])
    new_values = {
        "customer_id": customer_id,
        "delivery_date": data.delivery_date.isoformat() if data.delivery_date else None,
        "delivery_time": data.delivery_time,
        "delivery_time_text": data.delivery_time_text,
        "special_instructions": data.special_instructions,
    }
    changed = {k: v for k, v in new_values.items() if order[k] != v}
    for field, value in changed.items():
        orders_repo.add_history(conn, order_id, field, order[field], value)
    old_summary, new_summary = _summarise_items(order["items"]), _summarise_items(items)
    if old_summary != new_summary:
        orders_repo.add_history(conn, order_id, "items", old_summary, new_summary)
    orders_repo.update_order(conn, order_id, changed)
    orders_repo.replace_items(conn, order_id, items)
    return get_order_details(conn, shop_id, order_id)


def confirm_order(conn, shop_id: int, order_id: int) -> dict:
    order = get_order_details(conn, shop_id, order_id)
    if order["status"] == "confirmed":
        return order
    if order["status"] != "draft":
        raise InvalidRequest(f"Only draft orders can be confirmed (this one is {order['status']})")
    check_confirmable(order["items"])
    orders_repo.update_order(conn, order_id, {
        "status": "confirmed",
        "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    orders_repo.clear_review_flags(conn, order_id)
    orders_repo.add_history(conn, order_id, "status", "draft", "confirmed")
    return get_order_details(conn, shop_id, order_id)


def change_status(conn, shop_id: int, order_id: int, new_status: str) -> dict:
    order = get_order_details(conn, shop_id, order_id)
    current = order["status"]
    if new_status == current:
        return order
    if new_status == "confirmed":
        raise InvalidRequest("Use 'Confirm and Save' to confirm an order")
    if new_status not in ALLOWED_MOVES[current]:
        raise InvalidRequest(f"An order cannot move from {current} to {new_status}")
    orders_repo.update_order(conn, order_id, {"status": new_status})
    orders_repo.add_history(conn, order_id, "status", current, new_status)
    return get_order_details(conn, shop_id, order_id)


def find_possible_duplicates(conn, shop_id: int, customer_id: Optional[int],
                             product_names: list[str],
                             exclude_id: Optional[int] = None) -> list[dict]:
    """Orders for the same customer in the last 24 hours sharing at least one product."""
    if not customer_id:
        return []
    since = (datetime.now(timezone.utc) - DUPLICATE_WINDOW).isoformat(timespec="seconds")
    wanted = {n.strip().lower() for n in product_names if n.strip()}
    result = []
    for order in orders_repo.recent_orders_for_customer(conn, shop_id, customer_id, since,
                                                        exclude_id):
        names = {i["product_name"].lower() for i in orders_repo.get_items(conn, order["id"])}
        if not wanted or names & wanted:
            result.append(order)
    return result
