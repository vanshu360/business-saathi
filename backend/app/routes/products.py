import sqlite3

from fastapi import APIRouter, Depends

from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn
from ..repositories import products as repo
from ..schemas import AliasIn, ProductIn
from ..services import catalogue

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
def list_products(q: str = "", include_inactive: bool = False,
                  conn: sqlite3.Connection = Depends(db_conn)) -> list[dict]:
    return repo.list_products(conn, SHOP, q.strip(), include_inactive)


@router.post("", status_code=201)
def create_product(data: ProductIn, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.create_product(conn, SHOP, data)


@router.get("/{product_id}")
def get_product(product_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.require_product(conn, SHOP, product_id)


@router.put("/{product_id}")
def update_product(product_id: int, data: ProductIn,
                   conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.update_product(conn, SHOP, product_id, data)


@router.delete("/{product_id}")
def deactivate_product(product_id: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.deactivate_product(conn, SHOP, product_id)


@router.post("/{product_id}/aliases", status_code=201)
def add_alias(product_id: int, data: AliasIn,
              conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.add_alias(conn, SHOP, product_id, data)


@router.delete("/{product_id}/aliases/{alias_id}")
def delete_alias(product_id: int, alias_id: int,
                 conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    return catalogue.delete_alias(conn, SHOP, product_id, alias_id)
