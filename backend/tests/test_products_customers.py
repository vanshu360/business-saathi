def test_builtin_grocery_list_seeded(client):
    rice = [p for p in client.get("/api/products?q=chawal").json()]
    assert [p["name"] for p in rice] == ["Rice"]


def test_create_and_search_product_with_aliases(client):
    res = client.post("/api/products", json={
        "name": "Semolina", "default_unit": "kg", "aliases": ["sooji", "सूजी", "Sooji"]})
    assert res.status_code == 201
    product = res.json()
    assert product["price"] is None
    assert sorted(a["alias"] for a in product["aliases"]) == ["sooji", "सूजी"]

    assert [p["name"] for p in client.get("/api/products?q=sooj").json()] == ["Semolina"]
    assert [p["name"] for p in client.get("/api/products?q=सूजी").json()] == ["Semolina"]


def test_duplicate_product_name_rejected(client):
    client.post("/api/products", json={"name": "Sugar", "default_unit": "kg"})
    res = client.post("/api/products", json={"name": "sugar", "default_unit": "kg"})
    assert res.status_code == 409


def test_invalid_unit_rejected(client):
    res = client.post("/api/products", json={"name": "Milk", "default_unit": "bucket"})
    assert res.status_code == 422


def test_deactivate_hides_product(client):
    before = len(client.get("/api/products").json())
    pid = client.post("/api/products", json={"name": "Jaggery", "default_unit": "kg"}).json()["id"]
    client.delete(f"/api/products/{pid}")
    assert len(client.get("/api/products").json()) == before
    assert len(client.get("/api/products?include_inactive=true").json()) == before + 1


def test_alias_add_and_remove(client):
    pid = client.post("/api/products", json={"name": "Mustard oil", "default_unit": "l"}).json()["id"]
    product = client.post(f"/api/products/{pid}/aliases", json={"alias": "tel"}).json()
    alias_id = product["aliases"][0]["id"]
    product = client.delete(f"/api/products/{pid}/aliases/{alias_id}").json()
    assert product["aliases"] == []


def test_customer_phone_normalised_and_unique(client):
    res = client.post("/api/customers", json={"name": "Ramesh Kumar", "phone": "+91 98765 43210"})
    assert res.status_code == 201
    assert res.json()["phone"] == "9876543210"
    dup = client.post("/api/customers", json={"name": "Other", "phone": "09876543210"})
    assert dup.status_code == 409
    assert "Ramesh Kumar" in dup.json()["detail"]


def test_invalid_phone_rejected(client):
    res = client.post("/api/customers", json={"name": "X", "phone": "12345"})
    assert res.status_code == 422


def test_customer_search_and_update(client):
    cid = client.post("/api/customers", json={"name": "Sita Devi"}).json()["id"]
    assert len(client.get("/api/customers?q=sita").json()) == 1
    res = client.put(f"/api/customers/{cid}", json={"name": "Sita Devi", "phone": "9123456780"})
    assert res.json()["phone"] == "9123456780"
    assert client.get(f"/api/customers/{cid}").json()["orders"] == []


def test_unknown_customer_404(client):
    assert client.get("/api/customers/999").status_code == 404
