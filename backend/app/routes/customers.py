import sqlite3

from fastapi import APIRouter, Depends

from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn
from ..repositories import customers as repo
from ..schemas import CustomerIn
from ..services import customers as service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers(q: str = "", conn: sqlite3.Connection = Depends(db_conn)) -> list[dict]:
    return repo.list_customers(conn, SHOP, q.strip())


@router.post("", status_code=201)
def create_customer(data: CustomerIn, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.create_customer(conn, SHOP, data)


@router.get("/{customer_id}")
def get_customer(customer_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.get_customer_with_orders(conn, SHOP, customer_id)


@router.put("/{customer_id}")
def update_customer(customer_id: int, data: CustomerIn,
                    conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return service.update_customer(conn, SHOP, customer_id, data)
