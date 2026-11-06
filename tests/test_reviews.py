from app.models import UserRole


def deliver_order(client, customer, admin, menu, food_key="pizza"):
    """Place an order for one food and move it through the whole lifecycle."""
    order = client.post(
        "/orders",
        json={
            "restaurant_id": menu["restaurant"],
            "items": [{"food_id": menu[food_key], "quantity": 1}],
        },
        headers=customer,
    )
    order_id = order.json()["id"]
    for step in ["CONFIRMED", "PREPARING", "READY", "DELIVERED"]:
        client.patch(
            f"/orders/{order_id}/status", json={"status": step}, headers=admin
        )
    return order_id


def review(client, headers, food_id, rating=5, text="خوشمزه بود"):
    return client.post(
        "/reviews",
        json={"food_id": food_id, "rating": rating, "text": text},
        headers=headers,
    )


# ---------- who may review ----------

def test_review_requires_login(client, menu_data):
    assert client.post(
        "/reviews", json={"food_id": menu_data["pizza"], "rating": 5}
    ).status_code == 401


def test_cannot_review_without_any_order(client, login_as, menu_data):
    response = review(client, login_as(), menu_data["pizza"])
    assert response.status_code == 403


def test_cannot_review_food_from_undelivered_order(client, login_as, menu_data):
    customer = login_as()
    client.post(
        "/orders",
        json={"restaurant_id": menu_data["restaurant"],
              "items": [{"food_id": menu_data["pizza"], "quantity": 1}]},
        headers=customer,
    )  # stays PENDING
    assert review(client, customer, menu_data["pizza"]).status_code == 403


def test_cannot_review_food_that_was_not_in_delivered_order(
    client, login_as, menu_data
):
    customer, admin = login_as(), login_as(UserRole.ADMIN)
    deliver_order(client, customer, admin, menu_data, "pizza")
    assert review(client, customer, menu_data["cola"]).status_code == 403


def test_cannot_review_with_someone_elses_delivered_order(
    client, login_as, menu_data
):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    admin = login_as(UserRole.ADMIN)
    deliver_order(client, alice, admin, menu_data)
    assert review(client, bob, menu_data["pizza"]).status_code == 403


# ---------- creating reviews ----------

def test_review_after_delivery_succeeds(client, login_as, menu_data):
    customer, admin = login_as(), login_as(UserRole.ADMIN)
    deliver_order(client, customer, admin, menu_data)

    response = review(client, customer, menu_data["pizza"], rating=4)
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 4
    assert body["food_id"] == menu_data["pizza"]
    assert body["analysis"] is None
    assert "email" not in body


def test_rating_must_be_between_1_and_5(client, login_as, menu_data):
    customer, admin = login_as(), login_as(UserRole.ADMIN)
    deliver_order(client, customer, admin, menu_data)
    assert review(client, customer, menu_data["pizza"], rating=0).status_code == 422
    assert review(client, customer, menu_data["pizza"], rating=6).status_code == 422


def test_review_unknown_food_returns_404(client, login_as, menu_data):
    assert review(client, login_as(), 9999).status_code == 404


def test_duplicate_review_returns_409(client, login_as, menu_data):
    customer, admin = login_as(), login_as(UserRole.ADMIN)
    deliver_order(client, customer, admin, menu_data)
    assert review(client, customer, menu_data["pizza"]).status_code == 201
    assert review(client, customer, menu_data["pizza"]).status_code == 409


# ---------- restaurant rating ----------

def test_restaurant_rating_is_average_of_its_food_reviews(
    client, login_as, menu_data
):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    admin = login_as(UserRole.ADMIN)

    deliver_order(client, alice, admin, menu_data, "pizza")
    deliver_order(client, alice, admin, menu_data, "cola")
    deliver_order(client, bob, admin, menu_data, "pizza")

    review(client, alice, menu_data["pizza"], rating=5)
    review(client, bob, menu_data["pizza"], rating=4)
    review(client, alice, menu_data["cola"], rating=3)

    restaurant = client.get(f"/restaurants/{menu_data['restaurant']}").json()
    assert restaurant["rating"] == 4.0  # (5 + 4 + 3) / 3


def test_other_restaurants_are_not_affected(client, login_as, menu_data):
    customer, admin = login_as(), login_as(UserRole.ADMIN)
    deliver_order(client, customer, admin, menu_data)
    review(client, customer, menu_data["pizza"], rating=5)

    other = client.get(f"/restaurants/{menu_data['other_restaurant']}").json()
    assert other["rating"] == 0.0


# ---------- listing reviews ----------

def test_list_food_reviews_is_public_and_newest_first(client, login_as, menu_data):
    alice = login_as(UserRole.CUSTOMER, "alice@example.com")
    bob = login_as(UserRole.CUSTOMER, "bob@example.com")
    admin = login_as(UserRole.ADMIN)
    deliver_order(client, alice, admin, menu_data)
    deliver_order(client, bob, admin, menu_data)
    first = review(client, alice, menu_data["pizza"], rating=5).json()
    second = review(client, bob, menu_data["pizza"], rating=2).json()

    response = client.get(f"/foods/{menu_data['pizza']}/reviews")
    assert response.status_code == 200
    assert [r["id"] for r in response.json()] == [second["id"], first["id"]]

    limited = client.get(f"/foods/{menu_data['pizza']}/reviews", params={"limit": 1})
    assert len(limited.json()) == 1


def test_list_reviews_of_unknown_food_returns_404(client):
    assert client.get("/foods/9999/reviews").status_code == 404