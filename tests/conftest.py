import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app
from app.models import Food, Restaurant, User, UserRole
from app.security import hash_password


@pytest.fixture()
def db_session():
    """Fresh in-memory database for every test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def login_as(client, db_session):
    """Factory: create a user with a role and return its Authorization header."""

    def _login(role: UserRole = UserRole.CUSTOMER, email: str | None = None) -> dict:
        email = email or f"{role.value.lower()}@example.com"
        db_session.add(
            User(
                name="Test User",
                email=email,
                hashed_password=hash_password("secret1234"),
                role=role,
            )
        )
        db_session.commit()
        token = client.post(
            "/auth/login", data={"username": email, "password": "secret1234"}
        ).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture()
def menu_data(db_session) -> dict:
    """Two restaurants with a few foods; returns their ids."""
    pizza_place = Restaurant(name="Pizza Italia", address="Tehran")
    burger_place = Restaurant(name="Burger House", address="Tehran")
    db_session.add_all([pizza_place, burger_place])
    db_session.flush()

    pizza = Food(name="Pizza", category="pizza", price=300000,
                 restaurant_id=pizza_place.id)
    cola = Food(name="Cola", category="drink", price=50000,
                restaurant_id=pizza_place.id)
    sold_out = Food(name="Sold Out Pizza", category="pizza", price=100000,
                    restaurant_id=pizza_place.id, is_available=False)
    burger = Food(name="Burger", category="burger", price=250000,
                  restaurant_id=burger_place.id)
    db_session.add_all([pizza, cola, sold_out, burger])
    db_session.commit()

    return {
        "restaurant": pizza_place.id,
        "other_restaurant": burger_place.id,
        "pizza": pizza.id,
        "cola": cola.id,
        "sold_out": sold_out.id,
        "burger": burger.id,
    }