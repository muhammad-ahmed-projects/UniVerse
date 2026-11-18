from fastapi.testclient import TestClient

from tests.conftest import auth


def test_camera_crud_admin(client: TestClient, admin_token: str) -> None:
    h = auth(admin_token)
    created = client.post("/cameras", json={"name": "Lobby", "stream_source": "rtsp://10.0.0.5/s1"}, headers=h)
    assert created.status_code == 201
    cam_id = created.json()["id"]
    assert created.json()["status"] == "unknown"

    assert client.get(f"/cameras/{cam_id}", headers=h).json()["name"] == "Lobby"

    updated = client.put(f"/cameras/{cam_id}", json={"location": "Ground floor"}, headers=h)
    assert updated.status_code == 200
    assert updated.json()["location"] == "Ground floor"

    assert client.delete(f"/cameras/{cam_id}", headers=h).status_code == 204
    assert client.get(f"/cameras/{cam_id}", headers=h).status_code == 404


def test_camera_writes_are_admin_only(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    cam = seeded["camera_id"]
    assert client.get("/cameras", headers=h).status_code == 200
    assert client.post("/cameras", json={"name": "X", "stream_source": "0"}, headers=h).status_code == 403
    assert client.put(f"/cameras/{cam}", json={"name": "Y"}, headers=h).status_code == 403
    assert client.delete(f"/cameras/{cam}", headers=h).status_code == 403


def test_camera_validation(client: TestClient, admin_token: str) -> None:
    h = auth(admin_token)
    assert client.post("/cameras", json={"name": "", "stream_source": "0"}, headers=h).status_code == 422
    assert client.post("/cameras", json={"name": "No source"}, headers=h).status_code == 422
    assert client.get("/cameras/99999", headers=h).status_code == 404


def test_settings_defaults_and_update(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    h = auth(admin_token)
    cam = seeded["camera_id"]
    defaults = client.get(f"/cameras/{cam}/settings", headers=h)
    assert defaults.status_code == 200
    assert defaults.json()["loiter_seconds"] == 5.0
    assert defaults.json()["face_match_threshold"] == 0.45

    body = {**defaults.json(), "loiter_seconds": 12.5, "roi_x1": 0.1, "face_match_threshold": 0.6}
    body.pop("camera_id")
    saved = client.put(f"/cameras/{cam}/settings", json=body, headers=h)
    assert saved.status_code == 200
    reread = client.get(f"/cameras/{cam}/settings", headers=h).json()
    assert (reread["loiter_seconds"], reread["face_match_threshold"]) == (12.5, 0.6)


def test_settings_validation_and_rbac(
    client: TestClient, admin_token: str, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    bad_roi = {"roi_x1": 0.9, "roi_y1": 0.0, "roi_x2": 0.1, "roi_y2": 1.0}
    assert client.put(f"/cameras/{cam}/settings", json=bad_roi, headers=auth(admin_token)).status_code == 422
    assert (
        client.put(f"/cameras/{cam}/settings", json={"loiter_seconds": -1}, headers=auth(admin_token)).status_code
        == 422
    )
    for threshold in (0.1, 0.95):
        too_far = {"face_match_threshold": threshold}
        assert client.put(f"/cameras/{cam}/settings", json=too_far, headers=auth(admin_token)).status_code == 422
    assert client.put(f"/cameras/{cam}/settings", json={}, headers=auth(operator_token)).status_code == 403
    assert client.get("/cameras/99999/settings", headers=auth(admin_token)).status_code == 404


def test_heartbeat_updates_status(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)  # health scripts run as a non-admin service login
    cam = seeded["camera_id"]

    online = client.post(f"/cameras/{cam}/heartbeat", json={"status": "online"}, headers=h)
    assert online.status_code == 200
    assert online.json()["status"] == "online"
    assert online.json()["last_seen_at"] is not None

    offline = client.post(f"/cameras/{cam}/heartbeat", json={"status": "offline"}, headers=h)
    assert offline.json()["status"] == "offline"
    # last_seen_at keeps the last time the camera was actually seen.
    assert offline.json()["last_seen_at"] == online.json()["last_seen_at"]


def test_heartbeat_validation(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    h = auth(operator_token)
    cam = seeded["camera_id"]
    assert client.post(f"/cameras/{cam}/heartbeat", json={"status": "unknown"}, headers=h).status_code == 422
    assert client.post(f"/cameras/{cam}/heartbeat", json={"status": "melted"}, headers=h).status_code == 422
    assert client.post("/cameras/99999/heartbeat", json={"status": "online"}, headers=h).status_code == 404
    assert client.post(f"/cameras/{cam}/heartbeat", json={"status": "online"}).status_code == 401


def test_stream_credentials_are_masked(client: TestClient, admin_token: str, operator_token: str) -> None:
    source = "rtsp://admin:s3cret@192.168.1.64:554/Streaming/Channels/101"
    cam = client.post("/cameras", json={"name": "IP cam", "stream_source": source}, headers=auth(admin_token)).json()
    expected = "rtsp://admin:***@192.168.1.64:554/Streaming/Channels/101"
    assert cam["stream_source"] == expected
    for token in (admin_token, operator_token):
        listed = client.get("/cameras", headers=auth(token)).json()
        assert [c["stream_source"] for c in listed if c["id"] == cam["id"]] == [expected]
        assert "s3cret" not in client.get(f"/cameras/{cam['id']}", headers=auth(token)).text

    plain = client.post("/cameras", json={"name": "USB", "stream_source": "0"}, headers=auth(admin_token)).json()
    assert plain["stream_source"] == "0"
