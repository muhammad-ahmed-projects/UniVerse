from fastapi.testclient import TestClient

from tests.conftest import auth


def test_people_crud_admin(client: TestClient, admin_token: str) -> None:
    h = auth(admin_token)
    created = client.post("/people", json={"name": "Aiman", "notes": "consent form #2"}, headers=h)
    assert created.status_code == 201
    pid = created.json()["id"]
    assert [p["name"] for p in client.get("/people", headers=h).json()] == ["Aiman"]

    assert client.delete(f"/people/{pid}", headers=h).status_code == 204
    assert client.get(f"/people/{pid}", headers=h).status_code == 404
    assert client.delete(f"/people/{pid}", headers=h).status_code == 404


def test_people_writes_are_admin_only(client: TestClient, admin_token: str, operator_token: str) -> None:
    pid = client.post("/people", json={"name": "Khawaja"}, headers=auth(admin_token)).json()["id"]
    h = auth(operator_token)
    assert client.get("/people", headers=h).status_code == 200
    assert client.post("/people", json={"name": "X"}, headers=h).status_code == 403
    assert client.delete(f"/people/{pid}", headers=h).status_code == 403


def test_people_validation(client: TestClient, admin_token: str) -> None:
    assert client.post("/people", json={"name": ""}, headers=auth(admin_token)).status_code == 422
    assert client.post("/people", json={"name": "x" * 101}, headers=auth(admin_token)).status_code == 422
