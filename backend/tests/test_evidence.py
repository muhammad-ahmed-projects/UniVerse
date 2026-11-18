import os
import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models import AlertImage
from app.services import media_store, retention
from tests.conftest import auth, jpeg_bytes


def _alert(client: TestClient, token: str, camera_id: int) -> int:
    resp = client.post(
        "/alerts",
        json={"camera_id": camera_id, "alert_type": "LOITERING", "priority": "high", "message": "test"},
        headers=auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _upload(client: TestClient, token: str, alert_id: int, data: bytes | None = None):
    return client.post(
        f"/alerts/{alert_id}/images",
        files={"file": ("frame.jpg", data if data is not None else jpeg_bytes(), "image/jpeg")},
        headers=auth(token),
    )


def test_upload_list_and_download_evidence(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    alert_id = _alert(client, operator_token, seeded["camera_id"])
    created = _upload(client, operator_token, alert_id)
    assert created.status_code == 201, created.text
    image_id = created.json()["id"]

    alert = client.get(f"/alerts/{alert_id}", headers=auth(operator_token)).json()
    assert [img["id"] for img in alert["images"]] == [image_id]
    listed = client.get("/alerts", headers=auth(operator_token)).json()
    assert listed[0]["images"][0]["alert_id"] == alert_id

    file = client.get(f"/alerts/{alert_id}/images/{image_id}", headers=auth(operator_token))
    assert file.status_code == 200
    assert file.headers["content-type"] == "image/jpeg"
    assert file.content.startswith(b"\xff\xd8")


def test_incident_carries_its_alert_evidence(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    cam = seeded["camera_id"]
    alert_id = _alert(client, operator_token, cam)
    image_ids = [_upload(client, operator_token, alert_id).json()["id"] for _ in range(3)]

    incident = client.post(
        "/incidents",
        json={"camera_id": cam, "title": "Loitering", "source_alert_id": alert_id},
        headers=auth(operator_token),
    ).json()
    assert [img["id"] for img in incident["images"]] == image_ids

    # Images that arrive after promotion show up on the incident too.
    late = _upload(client, operator_token, alert_id).json()["id"]
    listed = client.get("/incidents", headers=auth(operator_token)).json()
    assert [img["id"] for img in listed[0]["images"]] == [*image_ids, late]


def test_evidence_upload_validation(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    alert_id = _alert(client, operator_token, seeded["camera_id"])
    assert _upload(client, operator_token, alert_id, b"not an image").status_code == 422
    assert _upload(client, operator_token, alert_id, b"").status_code == 422
    assert _upload(client, operator_token, 9999).status_code == 404
    assert client.post(f"/alerts/{alert_id}/images", files={"file": ("a.jpg", jpeg_bytes())}).status_code == 401

    for _ in range(10):
        assert _upload(client, operator_token, alert_id).status_code == 201
    assert _upload(client, operator_token, alert_id).status_code == 409


def test_evidence_download_needs_matching_alert_and_auth(
    client: TestClient, operator_token: str, seeded: dict[str, int]
) -> None:
    cam = seeded["camera_id"]
    a1, a2 = _alert(client, operator_token, cam), _alert(client, operator_token, cam)
    image_id = _upload(client, operator_token, a1).json()["id"]
    assert client.get(f"/alerts/{a2}/images/{image_id}", headers=auth(operator_token)).status_code == 404
    assert client.get(f"/alerts/{a1}/images/{image_id}").status_code == 401


def test_new_image_is_broadcast(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    alert_id = _alert(client, operator_token, seeded["camera_id"])
    with client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        image_id = _upload(client, operator_token, alert_id).json()["id"]
        msg = ws.receive_json()
    assert msg["type"] == "alert_image"
    assert msg["alert_id"] == alert_id
    assert msg["incident_id"] is None
    assert msg["image"]["id"] == image_id


def test_retention_purges_expired_images_and_orphans(
    client: TestClient, operator_token: str, seeded: dict[str, int]
) -> None:
    alert_id = _alert(client, operator_token, seeded["camera_id"])
    keep_id = _upload(client, operator_token, alert_id).json()["id"]
    old_id = _upload(client, operator_token, alert_id).json()["id"]

    with SessionLocal() as db:
        old = db.get(AlertImage, old_id)
        old.captured_at = datetime.now(UTC) - timedelta(days=31)
        old_file = old.file_name
        keep_file = db.get(AlertImage, keep_id).file_name
        db.commit()

    orphan = media_store.save("evidence", jpeg_bytes())
    stale = time.time() - retention.ORPHAN_GRACE_SECONDS - 60
    os.utime(media_store.media_root() / "evidence" / orphan, (stale, stale))
    fresh_orphan = media_store.save("evidence", jpeg_bytes())  # within the grace period: kept

    with SessionLocal() as db:
        result = retention.purge(db, days=30)

    assert result == {"expired": 1, "orphans": 1}
    assert media_store.path_for("evidence", old_file) is None
    assert media_store.path_for("evidence", orphan) is None
    assert media_store.path_for("evidence", keep_file) is not None
    assert media_store.path_for("evidence", fresh_orphan) is not None
    remaining = client.get(f"/alerts/{alert_id}", headers=auth(operator_token)).json()["images"]
    assert [img["id"] for img in remaining] == [keep_id]
    media_store.delete("evidence", fresh_orphan)


def test_retention_zero_keeps_everything(client: TestClient, operator_token: str, seeded: dict[str, int]) -> None:
    alert_id = _alert(client, operator_token, seeded["camera_id"])
    image_id = _upload(client, operator_token, alert_id).json()["id"]
    with SessionLocal() as db:
        db.get(AlertImage, image_id).captured_at = datetime.now(UTC) - timedelta(days=3650)
        db.commit()
        assert retention.purge(db, days=0)["expired"] == 0
