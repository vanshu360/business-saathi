"""Customer rules: avoid duplicate phone numbers."""
from ..errors import Conflict, NotFound
from ..repositories import customers as repo
from ..repositories import orders as orders_repo
from ..schemas import CustomerIn


def _check_phone_free(conn, shop_id: int, phone, own_id=None) -> None:
    if not phone:
        return
    existing = repo.find_by_phone(conn, shop_id, phone)
    if existing and existing["id"] != own_id:
        raise Conflict(f"This phone number already belongs to {existing['name']}")


def create_customer(conn, shop_id: int, data: CustomerIn) -> dict:
    _check_phone_free(conn, shop_id, data.phone)
    customer_id = repo.insert_customer(conn, shop_id, data.name, data.phone, data.notes)
    return repo.get_customer(conn, shop_id, customer_id)


def get_customer_with_orders(conn, shop_id: int, customer_id: int) -> dict:
    customer = repo.get_customer(conn, shop_id, customer_id)
    if not customer:
        raise NotFound("Customer not found")
    customer["orders"] = orders_repo.list_orders(conn, shop_id, customer_id=customer_id)
    return customer


def update_customer(conn, shop_id: int, customer_id: int, data: CustomerIn) -> dict:
    if not repo.get_customer(conn, shop_id, customer_id):
        raise NotFound("Customer not found")
    _check_phone_free(conn, shop_id, data.phone, own_id=customer_id)
    repo.update_customer(conn, customer_id, data.name, data.phone, data.notes)
    return repo.get_customer(conn, shop_id, customer_id)
