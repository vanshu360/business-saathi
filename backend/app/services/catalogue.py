"""Product catalogue rules (duplicate names, aliases, deactivation)."""
from ..errors import Conflict, NotFound
from ..repositories import products as repo
from ..schemas import AliasIn, ProductIn


def create_product(conn, shop_id: int, data: ProductIn, is_demo: bool = False) -> dict:
    if repo.find_by_name(conn, shop_id, data.name):
        raise Conflict(f"A product named '{data.name}' already exists")
    product_id = repo.insert_product(conn, shop_id, data.name, data.default_unit, data.price,
                                     is_demo)
    repo.replace_aliases(conn, product_id, data.aliases)
    return repo.get_product(conn, shop_id, product_id)


def require_product(conn, shop_id: int, product_id: int) -> dict:
    product = repo.get_product(conn, shop_id, product_id)
    if not product:
        raise NotFound("Product not found")
    return product


def update_product(conn, shop_id: int, product_id: int, data: ProductIn) -> dict:
    require_product(conn, shop_id, product_id)
    same_name = repo.find_by_name(conn, shop_id, data.name)
    if same_name and same_name["id"] != product_id:
        raise Conflict(f"A product named '{data.name}' already exists")
    repo.update_product(conn, product_id, data.name, data.default_unit, data.price)
    repo.replace_aliases(conn, product_id, data.aliases)
    return repo.get_product(conn, shop_id, product_id)


def deactivate_product(conn, shop_id: int, product_id: int) -> dict:
    require_product(conn, shop_id, product_id)
    repo.deactivate_product(conn, product_id)
    return repo.get_product(conn, shop_id, product_id)


def add_alias(conn, shop_id: int, product_id: int, data: AliasIn) -> dict:
    require_product(conn, shop_id, product_id)
    repo.add_alias(conn, product_id, " ".join(data.alias.split()), data.language_code)
    return repo.get_product(conn, shop_id, product_id)


def delete_alias(conn, shop_id: int, product_id: int, alias_id: int) -> dict:
    require_product(conn, shop_id, product_id)
    if not repo.delete_alias(conn, product_id, alias_id):
        raise NotFound("Alias not found")
    return repo.get_product(conn, shop_id, product_id)
