"""Live view: AI scripts POST frames, dashboards receive them over /ws/stream."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.services import frame_store as frame_store_module
from tests.conftest import auth, jpeg_bytes


def _post_frame(client: TestClient, token: str, camera_id: int, data: bytes, source: str = "roi_loitering", **kw):
    headers = {**auth(token), "Content-Type": kw.pop("content_type", "image/jpeg")}
    return client.post(f"/cameras/{camera_id}/frame?source={source}", content=data, headers=headers)


def _receive_frame(ws) -> tuple[int, bytes]:
    payload = ws.receive_bytes()
    return int.from_bytes(payload[:4], "big"), payload[4:]


def test_frame_reaches_subscribed_viewer(client: TestClient, ai_service_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    first, second = jpeg_bytes(320, 240), jpeg_bytes(160, 120)
    with client.websocket_connect(f"/ws/stream?token={ai_service_token}") as ws:
        ws.send_json({"subscribe": [cam]})
        assert _post_frame(client, ai_service_token, cam, first).status_code == 204
        assert _receive_frame(ws) == (cam, first)
        assert _post_frame(client, ai_service_token, cam, second).status_code == 204
        assert _receive_frame(ws) == (cam, second)


def test_new_subscriber_gets_current_frame_immediately(
    client: TestClient, ai_service_token: str, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    frame = jpeg_bytes()
    _post_frame(client, ai_service_token, cam, frame)
    with client.websocket_connect(f"/ws/stream?token={operator_token}") as ws:
        ws.send_json({"subscribe": [cam]})
        assert _receive_frame(ws) == (cam, frame)


def test_frame_validation(client: TestClient, ai_service_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    assert _post_frame(client, ai_service_token, cam, b"not a jpeg").status_code == 422
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), content_type="image/png").status_code == 415
    assert _post_frame(client, ai_service_token, cam, b"\xff\xd8\xff" + b"0" * (1024 * 1024)).status_code == 413
    assert _post_frame(client, ai_service_token, 9999, jpeg_bytes()).status_code == 404
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), source="Bad Source!").status_code == 422
    unauthenticated = client.post(f"/cameras/{cam}/frame", content=jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    assert unauthenticated.status_code == 401


def test_second_script_cannot_hijack_a_live_camera(
    client: TestClient, ai_service_token: str, seeded: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    cam = seeded["camera_id"]
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), source="roi_loitering").status_code == 204
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), source="tamper_detection").status_code == 409

    # Once the first script goes quiet, another one may take over.
    monkeypatch.setattr(frame_store_module, "STALE_AFTER_SECONDS", 0.0)
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), source="tamper_detection").status_code == 204


def test_detection_frames_take_over_from_health_monitor(
    client: TestClient, ai_service_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    health = f"/cameras/{cam}/frame?source=camera_health&priority=0"
    headers = {**auth(ai_service_token), "Content-Type": "image/jpeg"}
    assert client.post(health, content=jpeg_bytes(), headers=headers).status_code == 204
    assert _post_frame(client, ai_service_token, cam, jpeg_bytes(), source="roi_loitering").status_code == 204
    # ...and the raw health frames can't take the view back while detection is live.
    assert client.post(health, content=jpeg_bytes(), headers=headers).status_code == 409


def test_stream_rejects_bad_token(client: TestClient, seeded: dict[str, int]) -> None:
    for url in ("/ws/stream", "/ws/stream?token=garbage"):
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(url) as ws:
            ws.receive_bytes()


def test_stream_ignores_malformed_subscriptions(
    client: TestClient, ai_service_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    frame = jpeg_bytes()
    with client.websocket_connect(f"/ws/stream?token={ai_service_token}") as ws:
        ws.send_text("not json")
        ws.send_json({"subscribe": "everything"})
        ws.send_json({"subscribe": [True]})
        ws.send_json({"subscribe": [cam]})  # the socket survived the junk above
        _post_frame(client, ai_service_token, cam, frame)
        assert _receive_frame(ws) == (cam, frame)
