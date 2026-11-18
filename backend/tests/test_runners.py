"""Starting/stopping a camera's AI scripts from the dashboard.

conftest replaces the real scripts with tiny fake processes (fake_command).
"""

import time
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.services.camera_runner import camera_runner
from tests.conftest import auth


def _wait_until(predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def _ip_camera(client: TestClient, admin_token: str) -> int:
    body = {"name": "Gate", "stream_source": "rtsp://user:secret@10.0.0.5:554/stream1"}
    return client.post("/cameras", json=body, headers=auth(admin_token)).json()["id"]


def _runner(client: TestClient, token: str, camera_id: int) -> dict:
    return client.get(f"/cameras/{camera_id}/runner", headers=auth(token)).json()


def test_start_watch_and_stop(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    h = auth(admin_token)
    assert _runner(client, admin_token, cam) == {
        "camera_id": cam,
        "running": False,
        "is_webcam": True,
        "scripts": [],
        "log": [],
    }

    started = client.post(f"/cameras/{cam}/runner", json={"scripts": ["roi_loitering"]}, headers=h)
    assert started.status_code == 200, started.text
    assert started.json()["running"] is True
    assert [s["name"] for s in started.json()["scripts"]] == ["roi_loitering"]

    assert _wait_until(lambda: "[roi_loitering] started roi_loitering" in _runner(client, admin_token, cam)["log"])
    listed = client.get("/camera-runners", headers=h).json()
    assert [(r["camera_id"], r["running"]) for r in listed] == [(cam, True)]

    stopped = client.delete(f"/cameras/{cam}/runner", headers=h)
    assert stopped.status_code == 200
    assert stopped.json()["running"] is False
    assert stopped.json()["scripts"][0]["running"] is False
    assert stopped.json()["scripts"][0]["stopped_by_user"] is True
    # Nobody is watching the camera any more.
    assert client.get(f"/cameras/{cam}", headers=h).json()["status"] == "unknown"


def test_webcam_allows_one_analysis(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]  # stream_source "0"
    resp = client.post(
        f"/cameras/{cam}/runner",
        json={"scripts": ["roi_loitering", "camera_health"]},
        headers=auth(admin_token),
    )
    assert resp.status_code == 409
    assert "USB webcam" in resp.json()["detail"]


def test_ip_camera_runs_several_and_rejects_double_start(
    client: TestClient, admin_token: str, seeded: dict[str, int]
) -> None:
    cam = _ip_camera(client, admin_token)
    h = auth(admin_token)
    resp = client.post(f"/cameras/{cam}/runner", json={"scripts": ["roi_loitering", "tamper_detection"]}, headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_webcam"] is False
    assert len(resp.json()["scripts"]) == 2

    again = client.post(f"/cameras/{cam}/runner", json={"scripts": ["face_recognition"]}, headers=h)
    assert again.status_code == 409
    assert "already running" in again.json()["detail"]

    # The camera password never reaches the dashboard log.
    log = " ".join(_runner(client, admin_token, cam)["log"])
    assert "secret" not in log and "user:***@10.0.0.5" in log


def test_start_stop_is_admin_only(
    client: TestClient, admin_token: str, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    h = auth(operator_token)
    assert client.post(f"/cameras/{cam}/runner", json={"scripts": ["roi_loitering"]}, headers=h).status_code == 403
    assert client.delete(f"/cameras/{cam}/runner", headers=h).status_code == 403
    assert client.get(f"/cameras/{cam}/runner", headers=h).status_code == 200
    assert client.get("/camera-runners", headers=h).status_code == 200


def test_start_validation(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    h = auth(admin_token)
    for scripts in ([], ["rm -rf /"], ["roi_loitering", "roi_loitering"]):
        assert client.post(f"/cameras/{cam}/runner", json={"scripts": scripts}, headers=h).status_code == 422
    assert client.post("/cameras/9999/runner", json={"scripts": ["roi_loitering"]}, headers=h).status_code == 404
    assert client.get("/cameras/9999/runner", headers=h).status_code == 404


def test_script_that_dies_marks_camera_offline(
    client: TestClient, admin_token: str, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    with client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        client.post(f"/cameras/{cam}/runner", json={"scripts": ["camera_health"]}, headers=auth(admin_token))
        messages = [ws.receive_json() for _ in range(3)]

    assert {"type": "camera_runner", "camera_id": cam, "running": True} in messages
    assert {"type": "camera_runner", "camera_id": cam, "running": False} in messages
    assert {"type": "camera_status", "camera_id": cam, "status": "offline"} in messages
    runner = _runner(client, admin_token, cam)
    assert runner["running"] is False
    assert runner["scripts"][0]["exit_code"] == 3
    assert runner["scripts"][0]["stopped_by_user"] is False
    assert any("Could not open source" in line for line in runner["log"])
    assert any("exited with code 3" in line for line in runner["log"])


def test_deleting_camera_stops_its_scripts(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = _ip_camera(client, admin_token)
    client.post(f"/cameras/{cam}/runner", json={"scripts": ["roi_loitering"]}, headers=auth(admin_token))
    process = camera_runner.get(cam).scripts[0].process
    assert client.delete(f"/cameras/{cam}", headers=auth(admin_token)).status_code == 204
    assert process.poll() is not None
    assert camera_runner.get(cam) is None


def test_masked_stream_source_cannot_be_saved(client: TestClient, admin_token: str, seeded: dict[str, int]) -> None:
    cam = _ip_camera(client, admin_token)
    masked = client.get(f"/cameras/{cam}", headers=auth(admin_token)).json()["stream_source"]
    assert masked == "rtsp://user:***@10.0.0.5:554/stream1"
    resp = client.put(f"/cameras/{cam}", json={"stream_source": masked}, headers=auth(admin_token))
    assert resp.status_code == 422
    assert "retype the full stream URL" in resp.text
    renamed = client.put(f"/cameras/{cam}", json={"name": "Back gate"}, headers=auth(admin_token))
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Back gate"
