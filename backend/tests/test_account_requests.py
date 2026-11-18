"""Self-service "Create account" and "Forgot password?" from the sign-in page."""

from fastapi.testclient import TestClient

from app.api import auth as auth_api
from tests.conftest import OPERATOR, auth


def _signup(client: TestClient, username: str = "newbie", password: str = "newbie-pass-1"):
    return client.post(
        "/auth/signup", json={"username": username, "email": f"{username}@example.com", "password": password}
    )


def _user(client: TestClient, admin_token: str, username: str) -> dict:
    return next(u for u in client.get("/users", headers=auth(admin_token)).json() if u["username"] == username)


def test_signup_is_pending_until_approved(client: TestClient, admin_token: str, operator_token: str) -> None:
    with client.websocket_connect(f"/ws/alerts?token={admin_token}") as ws:
        resp = _signup(client)
        assert ws.receive_json() == {"type": "account_request", "kind": "signup"}
    assert resp.status_code == 202
    assert "admin approves" in resp.json()["detail"]

    login = client.post("/auth/login", data={"username": "newbie", "password": "newbie-pass-1"})
    assert login.status_code == 403 and "waiting for an admin" in login.json()["detail"]
    # The pending state isn't revealed to someone with the wrong password.
    assert client.post("/auth/login", data={"username": "newbie", "password": "wrong-pass-1"}).status_code == 401

    pending = _user(client, admin_token, "newbie")
    assert (pending["is_pending"], pending["is_active"]) == (True, False)
    assert client.get("/users/requests", headers=auth(admin_token)).json() == {"signups": 1, "password_resets": 0}

    # Approving is admin-only, picks the role, and lets them in.
    assert (
        client.post(f"/users/{pending['id']}/approve", json={"role": "admin"}, headers=auth(operator_token)).status_code
        == 403
    )
    approved = client.post(
        f"/users/{pending['id']}/approve", json={"role": "security_operator"}, headers=auth(admin_token)
    )
    assert approved.status_code == 200
    assert (approved.json()["is_pending"], approved.json()["is_active"]) == (False, True)
    assert client.post("/auth/login", data={"username": "newbie", "password": "newbie-pass-1"}).status_code == 200
    again = client.post(f"/users/{pending['id']}/approve", json={}, headers=auth(admin_token))
    assert again.status_code == 400


def test_reject_and_signup_validation(client: TestClient, admin_token: str) -> None:
    assert _signup(client).status_code == 202
    assert _signup(client).status_code == 400  # username taken
    assert _signup(client, OPERATOR[0]).status_code == 400
    for body in (
        {"username": "x", "password": "long-enough-1"},
        {"username": "has space", "password": "long-enough-1"},
        {"username": "okname", "password": "short"},
        {"username": "okname", "password": "long-enough-1", "role": "admin", "email": "not-an-email"},
    ):
        assert client.post("/auth/signup", json=body).status_code == 422

    pending = _user(client, admin_token, "newbie")
    # A pending request can't be edited into an active account; approve or reject it.
    edit = client.patch(f"/users/{pending['id']}", json={"is_active": True}, headers=auth(admin_token))
    assert edit.status_code == 400
    assert client.delete(f"/users/{pending['id']}", headers=auth(admin_token)).status_code == 204
    assert client.post("/auth/login", data={"username": "newbie", "password": "newbie-pass-1"}).status_code == 401


def test_signup_role_cannot_be_chosen_by_the_requester(client: TestClient, admin_token: str) -> None:
    body = {"username": "sneaky", "password": "sneaky-pass-1", "role": "admin"}
    assert client.post("/auth/signup", json=body).status_code == 202
    assert _user(client, admin_token, "sneaky")["role"] == "security_operator"


def test_pending_queue_is_capped(client: TestClient, admin_token: str, monkeypatch) -> None:
    monkeypatch.setattr(auth_api, "MAX_PENDING_SIGNUPS", 2)
    assert _signup(client, "one").status_code == 202
    assert _signup(client, "two").status_code == 202
    assert _signup(client, "three").status_code == 429


def test_forgot_password_request_flow(client: TestClient, admin_token: str, operator_token: str) -> None:
    same = "If that account exists, an admin has been asked to reset its password. They will give you the new one."
    with client.websocket_connect(f"/ws/alerts?token={admin_token}") as ws:
        resp = client.post("/auth/forgot-password", json={"username": OPERATOR[0]})
        assert ws.receive_json() == {"type": "account_request", "kind": "password_reset"}
    assert resp.status_code == 202 and resp.json()["detail"] == same
    # Unknown usernames get exactly the same answer (no account discovery).
    unknown = client.post("/auth/forgot-password", json={"username": "nobody-here"})
    assert unknown.status_code == 202 and unknown.json()["detail"] == same

    op = _user(client, admin_token, OPERATOR[0])
    assert op["password_reset_requested_at"] is not None
    assert client.get("/users/requests", headers=auth(admin_token)).json() == {"signups": 0, "password_resets": 1}
    # Asking again doesn't stack requests.
    client.post("/auth/forgot-password", json={"username": OPERATOR[0]})
    assert client.get("/users/requests", headers=auth(admin_token)).json()["password_resets"] == 1

    # The admin's reset closes the request; the old password stops working.
    client.post(f"/users/{op['id']}/password", json={"new_password": "reset-by-admin-1"}, headers=auth(admin_token))
    assert _user(client, admin_token, OPERATOR[0])["password_reset_requested_at"] is None
    assert client.post("/auth/login", data={"username": OPERATOR[0], "password": "reset-by-admin-1"}).status_code == 200
    assert client.get("/users/requests", headers=auth(operator_token)).status_code in (401, 403)


def test_dismiss_reset_request(client: TestClient, admin_token: str) -> None:
    client.post("/auth/forgot-password", json={"username": OPERATOR[0]})
    op = _user(client, admin_token, OPERATOR[0])
    dismissed = client.post(f"/users/{op['id']}/dismiss-reset", headers=auth(admin_token))
    assert dismissed.status_code == 200 and dismissed.json()["password_reset_requested_at"] is None


def test_pending_accounts_cannot_request_password_resets(client: TestClient, admin_token: str) -> None:
    _signup(client)
    client.post("/auth/forgot-password", json={"username": "newbie"})
    assert client.get("/users/requests", headers=auth(admin_token)).json() == {"signups": 1, "password_resets": 0}
