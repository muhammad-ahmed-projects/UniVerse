import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.db.session import SessionLocal
from app.models import Camera, Incident, User
from tests.conftest import ADMIN, OPERATOR, _token, auth


def _user_id(username: str) -> int:
    with SessionLocal() as db:
        return db.query(User).filter_by(username=username).one().id


def _create(client: TestClient, admin_token: str, username: str = "guard1", role: str = "security_operator"):
    return client.post(
        "/users",
        json={"username": username, "email": f"{username}@example.com", "password": "guard-pass-1", "role": role},
        headers=auth(admin_token),
    )


def test_admin_lists_and_creates_users(client: TestClient, admin_token: str) -> None:
    names = [u["username"] for u in client.get("/users", headers=auth(admin_token)).json()]
    assert names == ["admin_t", "operator_t", "ai_service_t"]

    created = _create(client, admin_token)
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "security_operator"
    assert "password" not in created.text and "hashed" not in created.text
    assert client.post("/auth/login", data={"username": "guard1", "password": "guard-pass-1"}).status_code == 200


def test_create_validation(client: TestClient, admin_token: str) -> None:
    assert _create(client, admin_token).status_code == 201
    assert _create(client, admin_token).status_code == 400  # duplicate username
    other = client.post(
        "/users",
        json={"username": "guard2", "email": "guard1@example.com", "password": "guard-pass-1"},
        headers=auth(admin_token),
    )
    assert other.status_code == 400 and "already in use" in other.json()["detail"]
    for body in (
        {"username": "has space", "password": "guard-pass-1"},
        {"username": "ok_name", "password": "short"},
        {"username": "ok_name", "password": "guard-pass-1", "role": "superuser"},
    ):
        assert client.post("/users", json=body, headers=auth(admin_token)).status_code == 422


def test_user_management_is_admin_only(client: TestClient, admin_token: str, operator_token: str) -> None:
    h = auth(operator_token)
    admin_id = _user_id(ADMIN[0])
    assert client.get("/users", headers=h).status_code == 403
    assert _create(client, operator_token).status_code == 403
    assert client.patch(f"/users/{admin_id}", json={"is_active": False}, headers=h).status_code == 403
    assert (
        client.post(f"/users/{admin_id}/password", json={"new_password": "hacked-pass"}, headers=h).status_code == 403
    )
    assert client.delete(f"/users/{admin_id}", headers=h).status_code == 403


def test_edit_role_email_and_deactivate(client: TestClient, admin_token: str, operator_token: str) -> None:
    op_id = _user_id(OPERATOR[0])
    h = auth(admin_token)
    updated = client.patch(f"/users/{op_id}", json={"role": "admin", "email": "op@example.com"}, headers=h)
    assert updated.status_code == 200
    assert (updated.json()["role"], updated.json()["email"]) == ("admin", "op@example.com")

    client.patch(f"/users/{op_id}", json={"is_active": False}, headers=h)
    # The deactivated account's live token stops working, and it can't log in again.
    assert client.get("/auth/me", headers=auth(operator_token)).status_code == 401
    assert client.post("/auth/login", data={"username": OPERATOR[0], "password": OPERATOR[1]}).status_code == 403
    assert client.patch("/users/9999", json={"is_active": True}, headers=h).status_code == 404


def test_admin_cannot_lock_themselves_out(client: TestClient, admin_token: str) -> None:
    admin_id = _user_id(ADMIN[0])
    h = auth(admin_token)
    for body in ({"role": "security_operator"}, {"is_active": False}):
        resp = client.patch(f"/users/{admin_id}", json=body, headers=h)
        assert resp.status_code == 400 and "your own" in resp.json()["detail"]
    assert client.delete(f"/users/{admin_id}", headers=h).status_code == 400
    # Editing their own email is fine.
    assert client.patch(f"/users/{admin_id}", json={"email": "boss@example.com"}, headers=h).status_code == 200


def test_reset_password_logs_out_old_sessions(client: TestClient, admin_token: str, operator_token: str) -> None:
    op_id = _user_id(OPERATOR[0])
    resp = client.post(f"/users/{op_id}/password", json={"new_password": "brand-new-pass"}, headers=auth(admin_token))
    assert resp.status_code == 204
    assert client.get("/auth/me", headers=auth(operator_token)).status_code == 401
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        ws.receive_json()
    assert client.post("/auth/login", data={"username": OPERATOR[0], "password": OPERATOR[1]}).status_code == 401
    new = client.post("/auth/login", data={"username": OPERATOR[0], "password": "brand-new-pass"})
    assert new.status_code == 200
    assert client.get("/auth/me", headers=auth(new.json()["access_token"])).status_code == 200


def test_change_own_password(client: TestClient, operator_token: str) -> None:
    h = auth(operator_token)
    wrong = client.post("/auth/change-password", json={"current_password": "nope", "new_password": "x" * 10}, headers=h)
    assert wrong.status_code == 400 and "incorrect" in wrong.json()["detail"]
    same = client.post(
        "/auth/change-password", json={"current_password": OPERATOR[1], "new_password": OPERATOR[1]}, headers=h
    )
    assert same.status_code == 400
    short = client.post(
        "/auth/change-password", json={"current_password": OPERATOR[1], "new_password": "abc"}, headers=h
    )
    assert short.status_code == 422

    ok = client.post(
        "/auth/change-password", json={"current_password": OPERATOR[1], "new_password": "my-new-secret"}, headers=h
    )
    assert ok.status_code == 200
    # This session continues with the returned token; the old token is dead.
    assert client.get("/auth/me", headers=auth(ok.json()["access_token"])).status_code == 200
    assert client.get("/auth/me", headers=h).status_code == 401
    assert client.post("/auth/login", data={"username": OPERATOR[0], "password": "my-new-secret"}).status_code == 200


def test_delete_user(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    h = auth(admin_token)
    guard_id = _create(client, admin_token).json()["id"]
    assert client.delete(f"/users/{guard_id}", headers=h).status_code == 204
    assert client.delete(f"/users/{guard_id}", headers=h).status_code == 404

    # Someone who reviewed an incident stays in the audit trail.
    reviewer_id = _create(client, admin_token, "reviewer").json()["id"]
    with SessionLocal() as db:
        cam = db.get(Camera, seeded["camera_id"])
        db.add(Incident(camera_id=cam.id, title="t", status="acknowledged", acknowledged_by=reviewer_id))
        db.commit()
    resp = client.delete(f"/users/{reviewer_id}", headers=h)
    assert resp.status_code == 409 and "Deactivate it instead" in resp.json()["detail"]
    assert client.patch(f"/users/{reviewer_id}", json={"is_active": False}, headers=h).status_code == 200


def test_tokens_from_before_this_change_still_work(client: TestClient, seeded: dict[str, int]) -> None:
    # Accounts that never changed their password keep working with any valid token.
    token = _token(client, ADMIN)
    assert client.get("/auth/me", headers=auth(token)).status_code == 200
