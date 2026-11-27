import sqlite3

from fastapi import APIRouter, Depends

from ..config import Settings
from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn, get_settings
from ..repositories import orders as orders_repo
from ..timeutils import local_day_bounds_utc, shop_today

router = APIRouter(prefix="/api", tags=["dashboard"])
OPEN_STATUSES = ["confirmed", "pending", "processing"]


@router.get("/dashboard")
def dashboard(conn: sqlite3.Connection = Depends(db_conn),
              settings: Settings = Depends(get_settings)) -> dict:
    start, end = local_day_bounds_utc(shop_today(settings.timezone), settings.timezone)

    def count(sql: str, params: tuple = ()) -> dict:
        row = conn.execute(
            f"SELECT COUNT(*) AS total, COALESCE(SUM(is_demo), 0) AS demo FROM {sql}",
            (SHOP, *params),
        ).fetchone()
        return {"total": row["total"], "demo": row["demo"]}

    marks = ",".join("?" * len(OPEN_STATUSES))
    return {
        "orders_today": count(
            "orders WHERE shop_id = ? AND created_at >= ? AND created_at < ?", (start, end)),
        "pending": count(f"orders WHERE shop_id = ? AND status IN ({marks})",
                         tuple(OPEN_STATUSES)),
        "drafts": count("orders WHERE shop_id = ? AND status = 'draft'"),
        "completed": count("orders WHERE shop_id = ? AND status = 'completed'"),
        "customers": count("customers WHERE shop_id = ?"),
        "recent_orders": orders_repo.list_orders(conn, SHOP, limit=8),
        "pending_orders": orders_repo.list_orders(conn, SHOP, statuses=OPEN_STATUSES, limit=8),
        "has_demo_data": bool(conn.execute(
            "SELECT 1 FROM orders WHERE shop_id = ? AND is_demo = 1 UNION "
            "SELECT 1 FROM customers WHERE shop_id = ? AND is_demo = 1 UNION "
            "SELECT 1 FROM products WHERE shop_id = ? AND is_demo = 1 LIMIT 1",
            (SHOP, SHOP, SHOP),
        ).fetchone()),
    }
