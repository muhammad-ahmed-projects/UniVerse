from fastapi.testclient import TestClient

from tests.conftest import ADMIN, OPERATOR, auth


def test_login_success_and_me(client: TestClient, seeded: dict[str, int]) -> None:
    resp = client.post("/auth/login", data={"username": OPERATOR[0], "password": OPERATOR[1]})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["username"] == OPERATOR[0]
    assert me.json()["role"] == "security_operator"
    assert "hashed_password" not in me.json()


def test_login_wrong_password(client: TestClient, seeded: dict[str, int]) -> None:
    resp = client.post("/auth/login", data={"username": ADMIN[0], "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient, seeded: dict[str, int]) -> None:
    resp = client.post("/auth/login", data={"username": "nobody", "password": "whatever"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client: TestClient, seeded: dict[str, int]) -> None:
    assert client.get("/cameras").status_code == 401
    assert client.get("/cameras", headers=auth("not-a-jwt")).status_code == 401


def test_register_is_admin_only(client: TestClient, admin_token: str, operator_token: str) -> None:
    body = {"username": "newop", "password": "long-enough-pw", "role": "security_operator"}
    assert client.post("/auth/register", json=body).status_code == 401
    assert client.post("/auth/register", json=body, headers=auth(operator_token)).status_code == 403

    resp = client.post("/auth/register", json=body, headers=auth(admin_token))
    assert resp.status_code == 201
    assert resp.json()["role"] == "security_operator"

    # The new account can actually log in.
    login = client.post("/auth/login", data={"username": "newop", "password": "long-enough-pw"})
    assert login.status_code == 200


def test_register_rejects_duplicate_and_short_password(client: TestClient, admin_token: str) -> None:
    dup = client.post(
        "/auth/register", json={"username": ADMIN[0], "password": "long-enough-pw"}, headers=auth(admin_token)
    )
    assert dup.status_code == 400

    short = client.post("/auth/register", json={"username": "x_user", "password": "short"}, headers=auth(admin_token))
    assert short.status_code == 422


def test_password_is_stored_hashed(client: TestClient, admin_token: str) -> None:
    from app.db.session import SessionLocal
    from app.models import User

    client.post(
        "/auth/register", json={"username": "hashcheck", "password": "plain-text-pw"}, headers=auth(admin_token)
    )
    with SessionLocal() as db:
        stored = db.query(User).filter_by(username="hashcheck").one().hashed_password
    assert stored != "plain-text-pw"
    assert stored.startswith("$2b$")
