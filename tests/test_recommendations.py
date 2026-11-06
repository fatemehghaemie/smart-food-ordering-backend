from app.models import Food, Order, OrderItem, OrderStatus, User, UserRole
from app.security import hash_password


def _add_user(db_session, email: str, role: UserRole = UserRole.CUSTOMER) -> User:
    user = User(
        name="Recommendation Tester",
        email=email,
        hashed_password=hash_password("secret1234"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _add_order(db_session, user: User, food_id: int, status: OrderStatus) -> Order:
    food = db_session.get(Food, food_id)
    order = Order(
        customer_id=user.id,
        restaurant_id=food.restaurant_id,
        status=status,
        total_price=food.price,
        items=[OrderItem(food_id=food.id, quantity=1, unit_price=food.price)],
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_personalized_recommendations_rank_similar_food_and_exclude_orders(
    client, db_session, menu_data
):
    user = _add_user(db_session, "recommend-user@example.com")
    similar_pizza = Food(
        name="Pizza with mozzarella",
        category="pizza",
        description="Pizza with tomato sauce",
        ingredients="dough, tomato, mozzarella",
        price=310000,
        restaurant_id=menu_data["restaurant"],
    )
    db_session.add(similar_pizza)
    db_session.commit()
    _add_order(db_session, user, menu_data["pizza"], OrderStatus.DELIVERED)

    response = client.get(f"/recommendations/{user.id}", headers=client_token(client, user))

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "personalized"
    assert body["recommendations"][0]["food"]["id"] == similar_pizza.id
    assert menu_data["pizza"] not in {
        item["food"]["id"] for item in body["recommendations"]
    }
    assert all(0 <= item["score"] <= 1 for item in body["recommendations"])


def test_user_without_history_gets_globally_popular_foods(
    client, db_session, login_as, menu_data
):
    previous_customer = _add_user(db_session, "previous-customer@example.com")
    _add_order(db_session, previous_customer, menu_data["pizza"], OrderStatus.DELIVERED)
    headers = login_as()

    user_id = client.get("/auth/me", headers=headers).json()["id"]
    response = client.get(f"/recommendations/{user_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "popular"
    assert body["recommendations"][0]["food"]["id"] == menu_data["pizza"]


def test_user_without_any_order_data_gets_empty_recommendations(
    client, login_as
):
    headers = login_as()
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    response = client.get(f"/recommendations/{user_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["strategy"] == "empty"
    assert response.json()["recommendations"] == []


def test_recommendations_require_login(client):
    assert client.get("/recommendations/1").status_code == 401


def test_customer_cannot_read_another_users_recommendations(
    client, login_as
):
    headers = login_as()

    assert client.get("/recommendations/999", headers=headers).status_code == 403


def test_admin_can_read_recommendations_for_another_user(
    client, login_as, db_session
):
    target = _add_user(db_session, "recommend-target@example.com")
    headers = login_as(UserRole.ADMIN)

    response = client.get(f"/recommendations/{target.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["user_id"] == target.id


def test_recommendation_limit_is_validated(client, login_as):
    headers = login_as()

    assert client.get("/recommendations/1?limit=0", headers=headers).status_code == 422


def client_token(client, user: User) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": user.email, "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
