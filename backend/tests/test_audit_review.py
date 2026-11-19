"""Audit log entries, and operator review of alerts (false-alarm rate)."""

from fastapi.testclient import TestClient

from tests.conftest import ADMIN, OPERATOR, auth


def _logs(client: TestClient, admin_token: str, **params) -> dict:
    resp = client.get("/audit-logs", params=params, headers=auth(admin_token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _actions(page: dict) -> list[str]:
    return [item["action"] for item in page["items"]]


def test_logins_and_failures_are_audited(client: TestClient, admin_token: str) -> None:
    client.post("/auth/login", data={"username": OPERATOR[0], "password": "Wrong-pass-1"})
    page = _logs(client, admin_token, category="auth")
    assert _actions(page)[:2] == ["auth.login_failed", "auth.login"]
    failed = page["items"][0]
    assert failed["actor_username"] == OPERATOR[0] and failed["actor_id"] is None
    assert failed["ip_address"]  # recorded
    assert page["items"][1]["actor_username"] == ADMIN[0]


def test_admin_actions_are_audited(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    h = auth(admin_token)
    cam = client.post("/cameras", json={"name": "Gate", "stream_source": "0"}, headers=h).json()["id"]
    client.put(f"/cameras/{cam}", json={"name": "Back gate"}, headers=h)
    person = client.post("/people", json={"name": "Aiman"}, headers=h).json()["id"]
    user = client.post("/users", json={"username": "guard9", "password": "Guard-pass-9"}, headers=h).json()["id"]
    client.post(f"/users/{user}/password", json={"new_password": "Other-pass-9"}, headers=h)
    client.delete(f"/users/{user}", headers=h)
    client.delete(f"/people/{person}", headers=h)
    client.delete(f"/cameras/{cam}", headers=h)

    actions = _actions(_logs(client, admin_token, limit=50))
    for expected in (
        "camera.create",
        "camera.update",
        "person.create",
        "user.create",
        "user.password_reset",
        "user.delete",
        "person.delete",
        "camera.delete",
    ):
        assert expected in actions
    deleted = next(i for i in _logs(client, admin_token, category="user")["items"] if i["action"] == "user.delete")
    assert deleted["target_type"] == "user" and deleted["details"] == {"username": "guard9"}
    assert deleted["actor_username"] == ADMIN[0]


def test_audit_log_filters_paging_and_access(client: TestClient, admin_token: str, operator_token: str) -> None:
    for i in range(3):
        client.post("/cameras", json={"name": f"Cam {i}", "stream_source": "0"}, headers=auth(admin_token))
    page = _logs(client, admin_token, category="camera", limit=2)
    assert page["total"] == 3 and len(page["items"]) == 2
    assert _logs(client, admin_token, q="operator_t")["total"] >= 1  # the operator's login
    assert client.get("/audit-logs", headers=auth(operator_token)).status_code == 403
    assert client.get("/audit-logs?category=Bad Value", headers=auth(admin_token)).status_code == 422


def _alert(client: TestClient, token: str, cam: int, alert_type: str = "ROI_ENTRY") -> int:
    body = {"camera_id": cam, "alert_type": alert_type, "priority": "medium", "message": "x"}
    return client.post("/alerts", json=body, headers=auth(token)).json()["id"]


def test_review_alerts_and_stats(
    client: TestClient, operator_token: str, admin_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    h = auth(operator_token)
    a1, a2, a3 = (_alert(client, operator_token, cam) for _ in range(3))
    _alert(client, operator_token, cam, "LOITERING")

    with client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        resp = client.patch(f"/alerts/{a1}/review", json={"review_status": "false_alarm"}, headers=h)
        assert ws.receive_json() == {"type": "alert_review", "alert_id": a1, "review_status": "false_alarm"}
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "false_alarm" and resp.json()["reviewed_by"] is not None
    client.patch(f"/alerts/{a2}/review", json={"review_status": "confirmed"}, headers=h)
    client.patch(f"/alerts/{a3}/review", json={"review_status": "confirmed"}, headers=h)

    stats = client.get("/alerts/review-stats", headers=h).json()
    roi = next(r for r in stats["by_type"] if r["alert_type"] == "ROI_ENTRY")
    assert (roi["confirmed"], roi["false_alarm"], roi["unreviewed"]) == (2, 1, 0)
    assert roi["precision"] == 0.667 and roi["false_alarm_rate"] == 0.333
    loit = next(r for r in stats["by_type"] if r["alert_type"] == "LOITERING")
    assert loit["precision"] is None and loit["unreviewed"] == 1
    assert stats["overall"]["total"] == 4

    # Clearing the verdict, validation, and the audit trail.
    cleared = client.patch(f"/alerts/{a1}/review", json={"review_status": None}, headers=h)
    assert cleared.json()["review_status"] is None and cleared.json()["reviewed_by"] is None
    assert client.patch(f"/alerts/{a1}/review", json={"review_status": "maybe"}, headers=h).status_code == 422
    assert client.patch("/alerts/9999/review", json={"review_status": "confirmed"}, headers=h).status_code == 404
    assert "alert.review" in _actions(_logs(client, admin_token, category="alert"))


def test_promoting_an_alert_confirms_it(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    h = auth(operator_token)
    alert_id = _alert(client, operator_token, cam)
    client.post("/incidents", json={"camera_id": cam, "title": "t", "source_alert_id": alert_id}, headers=h)
    alert = client.get(f"/alerts/{alert_id}", headers=h).json()
    assert alert["review_status"] == "confirmed"
    # It can't then be called a false alarm.
    resp = client.patch(f"/alerts/{alert_id}/review", json={"review_status": "false_alarm"}, headers=h)
    assert resp.status_code == 400


def test_unusual_activity_settings(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    h = auth(admin_token)
    defaults = client.get(f"/cameras/{cam}/settings", headers=h).json()
    assert (defaults["crowd_threshold"], defaults["running_speed"]) == (5, 0.6)
    assert (defaults["abandoned_seconds"], defaults["fall_seconds"]) == (30.0, 2.0)
    body = {k: v for k, v in defaults.items() if k != "camera_id"} | {"crowd_threshold": 0, "fall_seconds": 3.5}
    saved = client.put(f"/cameras/{cam}/settings", json=body, headers=h).json()
    assert (saved["crowd_threshold"], saved["fall_seconds"]) == (0, 3.5)
    bad = body | {"running_speed": -1}
    assert client.put(f"/cameras/{cam}/settings", json=bad, headers=h).status_code == 422
