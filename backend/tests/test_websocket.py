import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models import User
from tests.conftest import OPERATOR, auth


def test_ws_receives_alert_and_status_broadcasts(
    client: TestClient, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    with client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        client.post(
            "/alerts",
            json={"camera_id": cam, "alert_type": "TAMPER_COVERED", "priority": "high", "message": "lens covered"},
            headers=auth(operator_token),
        )
        msg = ws.receive_json()
        assert msg["type"] == "alert"
        assert msg["alert_type"] == "TAMPER_COVERED"
        assert msg["camera_id"] == cam

        client.post(f"/cameras/{cam}/heartbeat", json={"status": "online"}, headers=auth(operator_token))
        assert ws.receive_json() == {"type": "camera_status", "camera_id": cam, "status": "online"}


def test_ws_rejects_bad_token(client: TestClient, seeded: dict[str, int]) -> None:
    for url in ("/ws/alerts", "/ws/alerts?token=garbage"):
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(url) as ws:
            ws.receive_json()


def test_ws_rejects_deactivated_user(client: TestClient, seeded: dict[str, int]) -> None:
    token = create_access_token(subject=OPERATOR[0], role="security_operator")
    with SessionLocal() as db:
        db.query(User).filter_by(username=OPERATOR[0]).one().is_active = False
        db.commit()

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/alerts?token={token}") as ws:
        ws.receive_json()
