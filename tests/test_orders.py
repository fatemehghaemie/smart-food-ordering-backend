from app.models import Food, UserRole


def place_order(client, headers, menu, items=None, restaurant=None):
    payload = {
        "restaurant_id": restaurant or menu["restaurant"],
        "items": items
        or [
            {"food_id": menu["pizza"], "quantity": 2},
            {"food_id": menu["cola"], "quantity": 1},
        ],
    }
    return client.post("/orders", json=payload, headers=headers)


def set_status(client, headers, order_id, new_status):
    return client.patch(
        f"/orders/{order_id}/status", json={"status": new_status}, headers=headers
    )


# ---------- creating orders ----------

def test_create_order_calculates_total_server_side(client, login_as, menu_data):
    response = place_order(client, login_as(), menu_data)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["total_price"] == 2 * 300000 + 50000
    assert len(body["items"]) == 2
    assert {i["line_total"] for i in body["items"]} == {600000, 50000}


def test_create_order_requires_login(client, menu_data):
    response = client.post("/orders", json={"restaurant_id": 1, "items": []})
    assert response.status_code == 401


def test_duplicate_lines_are_merged(client, login_as, menu_data):
    items = [
        {"food_id": menu_data["pizza"], "quantity": 1},
        {"food_id": menu_data["pizza"], "quantity": 2},
    ]
    body = place_order(client, login_as(), menu_data, items).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["total_price"] == 900000


def test_unavailable_food_is_rejected(client, login_as, menu_data):
    items = [{"food_id": menu_data["sold_out"], "quantity": 1}]
    assert place_order(client, login_as(), menu_data, items).status_code == 422


def test_food_from_another_restaurant_is_rejected(client, login_as, menu_data):
    items = [{"food_id": menu_data["burger"], "quantity": 1}]
    assert place_order(client, login_as(), menu_data, items).status_code == 422


def test_unknown_food_is_rejected(client, login_as, menu_data):
    items = [{"food_id": 9999, "quantity": 1}]
    assert place_order(client, login_as(), menu_data, items).status_code == 422


def test_unknown_restaurant_returns_404(client, login_as, menu_data):
    response = place_order(client, login_as(), menu_data, restaurant=9999)
    assert response.status_code == 404


def test_empty_items_or_zero_quantity_returns_422(client, login_as, menu_data):
    headers = login_as()
    empty = client.post(
        "/orders", json={"restaurant_id": menu_data["restaurant"], "items": []},
        headers=headers,
    )
    assert empty.status_code == 422
    zero = place_order(
        client, headers, menu_data, [{"food_id": menu_data["pizza"], "quantity": 0}]
    )
    assert zero.status_code == 422


def test_order_keeps_price_snapshot_after_menu_price_change(
    client, db_session, login_as, menu_data
):
    headers = login_as()
    order = place_order(client, headers, menu_data).json()

    db_session.get(Food, menu_data["pizza"]).price = 999999
    db_session.commit()

    again = client.get(f"/orders/{order['id']}", headers=headers).json()
    assert again["total_price"] == 650000


# ---------- visibility ----------

def test_customer_sees_only_own_orders_and_admin_sees_all(client, login_as, menu_data):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    admin = login_as(UserRole.ADMIN)
    place_order(client, alice, menu_data)
    place_order(client, bob, menu_data)

    assert len(client.get("/orders", headers=alice).json()) == 1
    assert len(client.get("/orders", headers=bob).json()) == 1
    assert len(client.get("/orders", headers=admin).json()) == 2


def test_customer_cannot_see_someone_elses_order(client, login_as, menu_data):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    order_id = place_order(client, alice, menu_data).json()["id"]

    assert client.get(f"/orders/{order_id}", headers=bob).status_code == 404
    assert client.get(f"/orders/{order_id}", headers=alice).status_code == 200


def test_filter_orders_by_status(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    customer = login_as()
    first = place_order(client, customer, menu_data).json()["id"]
    place_order(client, customer, menu_data)
    set_status(client, admin, first, "CONFIRMED")

    confirmed = client.get("/orders", params={"status": "CONFIRMED"}, headers=customer)
    assert [o["id"] for o in confirmed.json()] == [first]


# ---------- status changes ----------

def test_customer_can_cancel_own_pending_order(client, login_as, menu_data):
    customer = login_as()
    order_id = place_order(client, customer, menu_data).json()["id"]
    response = set_status(client, customer, order_id, "CANCELLED")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_customer_cannot_confirm_order(client, login_as, menu_data):
    customer = login_as()
    order_id = place_order(client, customer, menu_data).json()["id"]
    assert set_status(client, customer, order_id, "CONFIRMED").status_code == 403


def test_other_customer_cannot_cancel_order(client, login_as, menu_data):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    order_id = place_order(client, alice, menu_data).json()["id"]
    assert set_status(client, bob, order_id, "CANCELLED").status_code == 404


def test_admin_can_walk_full_lifecycle(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    order_id = place_order(client, login_as(), menu_data).json()["id"]
    for step in ["CONFIRMED", "PREPARING", "READY", "DELIVERED"]:
        response = set_status(client, admin, order_id, step)
        assert response.status_code == 200
        assert response.json()["status"] == step


def test_delivered_order_cannot_return_to_preparing(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    order_id = place_order(client, login_as(), menu_data).json()["id"]
    for step in ["CONFIRMED", "PREPARING", "READY", "DELIVERED"]:
        set_status(client, admin, order_id, step)

    response = set_status(client, admin, order_id, "PREPARING")
    assert response.status_code == 409
    assert client.get(f"/orders/{order_id}", headers=admin).json()["status"] == "DELIVERED"


def test_admin_cannot_skip_steps(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    order_id = place_order(client, login_as(), menu_data).json()["id"]
    assert set_status(client, admin, order_id, "DELIVERED").status_code == 409


def test_cancelled_order_cannot_be_reconfirmed(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    customer = login_as()
    order_id = place_order(client, customer, menu_data).json()["id"]
    set_status(client, customer, order_id, "CANCELLED")
    assert set_status(client, admin, order_id, "CONFIRMED").status_code == 409


def test_customer_cannot_cancel_once_preparing(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    customer = login_as()
    order_id = place_order(client, customer, menu_data).json()["id"]
    set_status(client, admin, order_id, "CONFIRMED")
    set_status(client, admin, order_id, "PREPARING")
    assert set_status(client, customer, order_id, "CANCELLED").status_code == 409


def test_invalid_status_value_returns_422(client, login_as, menu_data):
    admin = login_as(UserRole.ADMIN)
    order_id = place_order(client, login_as(), menu_data).json()["id"]
    assert set_status(client, admin, order_id, "FLYING").status_code == 422