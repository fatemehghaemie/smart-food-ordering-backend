USER = {"name": "Ali Rezaei", "email": "Ali@Example.com", "password": "secret1234"}


def register(client, payload=None):
    return client.post("/auth/register", json=payload or USER)


def login(client, email="ali@example.com", password="secret1234"):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_register_success_hides_password_and_sets_customer_role(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ali@example.com"  # normalized to lowercase
    assert body["role"] == "CUSTOMER"
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_returns_409(client):
    register(client)
    assert register(client).status_code == 409


def test_register_short_password_returns_422(client):
    response = register(client, {**USER, "password": "123"})
    assert response.status_code == 422


def test_login_success_returns_token(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_returns_401(client):
    register(client)
    assert login(client, password="wrong-password").status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_valid_token(client):
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "ali@example.com"


def test_me_with_invalid_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401