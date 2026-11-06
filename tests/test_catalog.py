import pytest

from app.models import Food, Restaurant, User, UserRole
from app.security import hash_password


@pytest.fixture()
def sample_data(db_session):
    pizza_place = Restaurant(name="Pizza Italia", address="Tehran", rating=4.5)
    burger_place = Restaurant(name="Burger House", address="Tehran", rating=4.2)
    db_session.add_all([pizza_place, burger_place])
    db_session.flush()
    ids = {"pizza": pizza_place.id, "burger": burger_place.id}
    db_session.add_all(
        [
            Food(name="Margherita Pizza", category="pizza", price=320000,
                 ingredients="dough, tomato, mozzarella", restaurant_id=ids["pizza"]),
            Food(name="Old Special Pizza", category="pizza", price=400000,
                 restaurant_id=ids["pizza"], is_available=False),
            Food(name="Cheeseburger", category="burger", price=310000,
                 ingredients="bun, beef, cheddar", restaurant_id=ids["burger"]),
            Food(name="Veggie Burger", category="burger", price=260000,
                 restaurant_id=ids["burger"]),
        ]
    )
    db_session.commit()
    return ids


def auth_header(client, db_session, role: UserRole) -> dict:
    email = f"{role.value.lower()}@example.com"
    db_session.add(
        User(name="Test", email=email, hashed_password=hash_password("secret1234"),
             role=role)
    )
    db_session.commit()
    token = client.post(
        "/auth/login", data={"username": email, "password": "secret1234"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- restaurants ----------

def test_list_restaurants_is_public_and_sorted_by_rating(client, sample_data):
    response = client.get("/restaurants")
    assert response.status_code == 200
    assert [r["name"] for r in response.json()] == ["Pizza Italia", "Burger House"]


def test_restaurant_not_found_returns_404(client):
    assert client.get("/restaurants/999").status_code == 404


def test_menu_hides_unavailable_foods(client, sample_data):
    response = client.get(f"/restaurants/{sample_data['pizza']}/menu")
    assert response.status_code == 200
    assert [f["name"] for f in response.json()] == ["Margherita Pizza"]


def test_menu_of_unknown_restaurant_returns_404(client):
    assert client.get("/restaurants/999/menu").status_code == 404


# ---------- food search ----------

def test_search_by_text_is_case_insensitive(client, sample_data):
    response = client.get("/foods", params={"q": "burger"})
    assert {f["name"] for f in response.json()} == {"Cheeseburger", "Veggie Burger"}


def test_search_matches_ingredients(client, sample_data):
    response = client.get("/foods", params={"q": "mozzarella"})
    assert [f["name"] for f in response.json()] == ["Margherita Pizza"]


def test_filter_by_category_excludes_unavailable_by_default(client, sample_data):
    assert len(client.get("/foods", params={"category": "pizza"}).json()) == 1
    response = client.get("/foods", params={"category": "pizza", "only_available": False})
    assert len(response.json()) == 2


def test_filter_by_max_price(client, sample_data):
    response = client.get("/foods", params={"max_price": 300000})
    assert [f["name"] for f in response.json()] == ["Veggie Burger"]


def test_invalid_price_range_returns_422(client, sample_data):
    response = client.get("/foods", params={"min_price": 500, "max_price": 100})
    assert response.status_code == 422


def test_pagination_limit(client, sample_data):
    assert len(client.get("/foods", params={"limit": 1}).json()) == 1


def test_get_food_not_found(client):
    assert client.get("/foods/999").status_code == 404


# ---------- admin-only creation ----------

def test_create_restaurant_requires_login(client):
    payload = {"name": "New Place", "address": "Tehran"}
    assert client.post("/restaurants", json=payload).status_code == 401


def test_create_restaurant_forbidden_for_customer(client, db_session):
    headers = auth_header(client, db_session, UserRole.CUSTOMER)
    payload = {"name": "New Place", "address": "Tehran"}
    assert client.post("/restaurants", json=payload, headers=headers).status_code == 403


def test_admin_can_create_restaurant_and_food(client, db_session):
    headers = auth_header(client, db_session, UserRole.ADMIN)
    created = client.post(
        "/restaurants", json={"name": "New Place", "address": "Tehran"}, headers=headers
    )
    assert created.status_code == 201

    food = client.post(
        "/foods",
        json={"name": "Soup", "category": "soup", "price": 90000,
              "restaurant_id": created.json()["id"]},
        headers=headers,
    )
    assert food.status_code == 201
    assert food.json()["is_available"] is True


def test_create_food_validates_price_and_restaurant(client, db_session):
    headers = auth_header(client, db_session, UserRole.ADMIN)
    bad_price = {"name": "Soup", "category": "soup", "price": 0, "restaurant_id": 1}
    assert client.post("/foods", json=bad_price, headers=headers).status_code == 422
    unknown = {"name": "Soup", "category": "soup", "price": 100, "restaurant_id": 999}
    assert client.post("/foods", json=unknown, headers=headers).status_code == 404