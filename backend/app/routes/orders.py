import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from ..config import Settings
from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn, get_settings
from ..errors import InvalidRequest
from ..repositories import orders as repo
from ..schemas import OrderCreate, OrderUpdate, StatusChange
from ..services import orders as service
from ..timeutils import local_day_bounds_utc

router = APIRouter(prefix="/api/orders", tags=["orders"])
VALID_STATUSES = set(service.ALLOWED_MOVES)


class DuplicateCheck(BaseModel):
    customer_id: Optional[int] = None
    product_names: list[str] = Field(default_factory=list, max_length=100)
    exclude_order_id: Optional[int] = None


@router.get("")
def list_orders(q: str = "", status: str = "", date_from: Optional[date] = None,
                date_to: Optional[date] = None, customer_id: Optional[int] = None,
                product: str = "", conn: sqlite3.Connection = Depends(db_conn),
                settings: Settings = Depends(get_settings)) -> list[dict]:
    statuses = [s for s in status.split(",") if s]
    unknown = set(statuses) - VALID_STATUSES
    if unknown:
        raise InvalidRequest(f"Unknown status: {', '.join(sorted(unknown))}")
    created_from = local_day_bounds_utc(date_from, settings.timezone)[0] if date_from else None
    created_to = local_day_bounds_utc(date_to, settings.timezone)[1] if date_to else None
    return repo.list_orders(conn, SHOP, q=q.strip(), statuses=statuses,
                            created_from=created_from, created_to=created_to,
                            customer_id=customer_id, product=product.strip())


@router.post("", status_code=201)
def create_order(data: OrderCreate, response: Response,
                 conn: sqlite3.Connection = Depends(db_conn),
                 settings: Settings = Depends(get_settings)) -> dict:
    order, created = service.create_order(conn, settings, SHOP, data)
    if not created:
        response.status_code = 200
    return {**order, "already_saved": not created}


@router.post("/check-duplicates")
def check_duplicates(data: DuplicateCheck,
                     conn: sqlite3.Connection = Depends(db_conn)) -> list[dict]:
    return service.find_possible_duplicates(conn, SHOP, data.customer_id, data.product_names,
                                            data.exclude_order_id)


@router.get("/{order_id}")
def get_order(order_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.get_order_details(conn, SHOP, order_id)


@router.put("/{order_id}")
def update_order(order_id: int, data: OrderUpdate,
                 conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.update_order(conn, SHOP, order_id, data)


@router.post("/{order_id}/confirm")
def confirm_order(order_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.confirm_order(conn, SHOP, order_id)


@router.patch("/{order_id}/status")
def change_status(order_id: int, data: StatusChange,
                  conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.change_status(conn, SHOP, order_id, data.status)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.change_status(conn, SHOP, order_id, "cancelled")


@router.get("/{order_id}/possible-duplicates")
def possible_duplicates(order_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> list[dict]:
    order = service.get_order_details(conn, SHOP, order_id)
    names = [i["product_name"] for i in order["items"]]
    return service.find_possible_duplicates(conn, SHOP, order["customer_id"], names, order_id)
