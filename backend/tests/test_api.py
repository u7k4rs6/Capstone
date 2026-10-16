def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_database(client):
    assert client.get("/ready").json() == {"status": "READY"}


def test_create_item(client, item):
    assert item["id"] > 0
    assert item["sku"] == "MLK-OAT-1L"
    assert item["low_stock"] is False


def test_create_rejects_duplicate_sku(client, item):
    response = client.post("/api/items", json={"name": "Dupe", "sku": item["sku"]})
    assert response.status_code == 409


def test_create_validates_payload(client):
    response = client.post("/api/items", json={"name": "", "sku": "X", "quantity": -1})
    assert response.status_code == 422


def test_list_and_filter_items(client, item):
    client.post("/api/items", json={"name": "Paper Cups", "sku": "CUP-12", "quantity": 1, "reorder_level": 5})
    assert len(client.get("/api/items").json()) == 2
    low = client.get("/api/items", params={"low_stock": True}).json()
    assert [i["sku"] for i in low] == ["CUP-12"]
    assert len(client.get("/api/items", params={"q": "oat"}).json()) == 1


def test_get_item_and_404(client, item):
    assert client.get(f"/api/items/{item['id']}").json()["name"] == "Oat Milk 1L"
    assert client.get("/api/items/9999").status_code == 404


def test_update_item(client, item):
    response = client.put(f"/api/items/{item['id']}", json={"quantity": 2})
    assert response.status_code == 200
    assert response.json()["quantity"] == 2
    assert response.json()["low_stock"] is True


def test_adjust_stock(client, item):
    assert client.post(f"/api/items/{item['id']}/adjust", json={"delta": 5}).json()["quantity"] == 15
    assert client.post(f"/api/items/{item['id']}/adjust", json={"delta": -15}).json()["quantity"] == 0
    assert client.post(f"/api/items/{item['id']}/adjust", json={"delta": -1}).status_code == 400


def test_delete_item(client, item):
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404


def test_stats(client, item):
    client.post("/api/items", json={"name": "Cups", "sku": "CUP", "quantity": 0, "unit_price": 3, "category": "Packaging"})
    stats = client.get("/api/stats").json()
    assert stats["total_items"] == 2
    assert stats["total_units"] == 10
    assert stats["out_of_stock"] == 1
    assert stats["inventory_value"] == 25.0
    assert stats["categories"] == {"Dairy": 1, "Packaging": 1}


def test_metrics_endpoint(client):
    client.get("/api/items")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
