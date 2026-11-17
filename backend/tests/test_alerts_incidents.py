from fastapi.testclient import TestClient

from tests.conftest import auth


def _alert(client: TestClient, token: str, camera_id: int, **overrides: object) -> dict:
    body = {"camera_id": camera_id, "alert_type": "ROI_ENTRY", "priority": "medium", "message": "entered"}
    resp = client.post("/alerts", json={**body, **overrides}, headers=auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _incident_from(client: TestClient, token: str, alert: dict) -> dict:
    resp = client.post(
        "/incidents",
        json={"camera_id": alert["camera_id"], "title": "Review", "source_alert_id": alert["id"]},
        headers=auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_list_alerts(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    a1 = _alert(client, operator_token, cam)
    a2 = _alert(client, operator_token, cam, alert_type="LOITERING", priority="high", extra_data={"track_id": 3})
    assert a2["extra_data"] == {"track_id": 3}

    listed = client.get("/alerts", headers=auth(operator_token)).json()
    assert [a["id"] for a in listed] == [a2["id"], a1["id"]]  # newest first

    limited = client.get("/alerts?limit=1", headers=auth(operator_token)).json()
    assert len(limited) == 1

    assert client.get(f"/alerts?camera_id={cam + 1}", headers=auth(operator_token)).json() == []
    assert client.get(f"/alerts/{a1['id']}", headers=auth(operator_token)).status_code == 200
    assert client.get("/alerts/99999", headers=auth(operator_token)).status_code == 404


def test_alert_validation(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    cam = seeded["camera_id"]
    base = {"camera_id": cam, "alert_type": "X", "message": "m"}
    assert client.post("/alerts", json={**base, "priority": "urgent"}, headers=h).status_code == 422
    assert client.post("/alerts", json={**base, "message": ""}, headers=h).status_code == 422
    assert client.post("/alerts", json={**base, "camera_id": 99999}, headers=h).status_code == 400
    assert client.get("/alerts?limit=0", headers=h).status_code == 422
    assert client.get("/alerts?limit=10000", headers=h).status_code == 422


def test_full_review_flow(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    alert = _alert(client, operator_token, seeded["camera_id"])
    incident = _incident_from(client, operator_token, alert)
    assert incident["status"] == "open"

    # The alert is now linked and no longer "unresolved".
    assert client.get(f"/alerts/{alert['id']}", headers=auth(operator_token)).json()["incident_id"] == incident["id"]
    unresolved = client.get("/alerts?unresolved_only=true", headers=auth(operator_token)).json()
    assert alert["id"] not in [a["id"] for a in unresolved]

    ack = client.patch(f"/incidents/{incident['id']}/acknowledge", headers=auth(operator_token))
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_by"] is not None

    resolved = client.patch(f"/incidents/{incident['id']}/resolve", headers=auth(operator_token))
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] >= resolved.json()["acknowledged_at"]


def test_review_flow_guards(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    alert = _alert(client, operator_token, seeded["camera_id"])
    incident = _incident_from(client, operator_token, alert)
    iid = incident["id"]

    # Can't promote the same alert twice.
    dup = client.post(
        "/incidents",
        json={"camera_id": alert["camera_id"], "title": "Again", "source_alert_id": alert["id"]},
        headers=h,
    )
    assert dup.status_code == 400

    # Can't skip acknowledgement.
    assert client.patch(f"/incidents/{iid}/resolve", headers=h).status_code == 400

    assert client.patch(f"/incidents/{iid}/acknowledge", headers=h).status_code == 200
    assert client.patch(f"/incidents/{iid}/acknowledge", headers=h).status_code == 400
    assert client.patch(f"/incidents/{iid}/resolve", headers=h).status_code == 200
    assert client.patch(f"/incidents/{iid}/resolve", headers=h).status_code == 400
    assert client.patch("/incidents/99999/acknowledge", headers=h).status_code == 404


def test_incident_validation(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    h = auth(admin_token)
    cam = seeded["camera_id"]
    other_cam = client.post("/cameras", json={"name": "Other", "stream_source": "1"}, headers=h).json()["id"]
    alert = _alert(client, admin_token, cam)

    wrong_cam = client.post(
        "/incidents", json={"camera_id": other_cam, "title": "t", "source_alert_id": alert["id"]}, headers=h
    )
    assert wrong_cam.status_code == 400
    assert (
        client.post(
            "/incidents", json={"camera_id": cam, "title": "t", "source_alert_id": 99999}, headers=h
        ).status_code
        == 400
    )
    assert client.post("/incidents", json={"camera_id": cam, "title": ""}, headers=h).status_code == 422
    assert (
        client.post("/incidents", json={"camera_id": cam, "title": "t", "priority": "urgent"}, headers=h).status_code
        == 422
    )
    assert client.get("/incidents?status=bogus", headers=h).status_code == 422


def test_incident_status_filter(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    first = _incident_from(client, operator_token, _alert(client, operator_token, seeded["camera_id"]))
    _incident_from(client, operator_token, _alert(client, operator_token, seeded["camera_id"]))
    client.patch(f"/incidents/{first['id']}/acknowledge", headers=h)

    assert [i["id"] for i in client.get("/incidents?status=acknowledged", headers=h).json()] == [first["id"]]
    assert len(client.get("/incidents?status=open", headers=h).json()) == 1


def test_dashboard_summary(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    cam = seeded["camera_id"]
    client.post(f"/cameras/{cam}/heartbeat", json={"status": "online"}, headers=h)
    alert = _alert(client, operator_token, cam)
    _alert(client, operator_token, cam)
    _incident_from(client, operator_token, alert)

    summary = client.get("/dashboard/summary", headers=h).json()
    assert summary == {
        "cameras_total": 1,
        "cameras_online": 1,
        "alerts_total": 2,
        "alerts_unreviewed": 1,
        "incidents_open": 1,
        "people_registered": 0,
    }
    assert client.get("/dashboard/summary").status_code == 401
