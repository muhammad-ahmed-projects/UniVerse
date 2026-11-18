"""Dashboard face registration, embeddings for the recognizer, and sightings.

The real InsightFace model isn't loaded here: get_face_encoder is
overridden with a fake that returns whatever faces a test asks for.
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import media_store
from app.services.face_encoder import DetectedFace, get_face_encoder
from tests.conftest import auth, jpeg_bytes


class FakeEncoder:
    def __init__(self) -> None:
        self.faces: list[DetectedFace] = []

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        return self.faces


def _face(x1: int = 50, width: int = 120, value: float = 0.1) -> DetectedFace:
    return DetectedFace(bbox=(x1, 40, x1 + width, 40 + width), embedding=[value] * 512, score=0.9)


@pytest.fixture
def encoder() -> FakeEncoder:
    fake = FakeEncoder()
    app.dependency_overrides[get_face_encoder] = lambda: fake
    return fake


def _person(client: TestClient, admin_token: str, name: str = "Aiman") -> int:
    return client.post("/people", json={"name": name}, headers=auth(admin_token)).json()["id"]


def _add_face(client: TestClient, token: str, person_id: int, data: bytes | None = None):
    return client.post(
        f"/people/{person_id}/faces",
        files={"file": ("face.jpg", data if data is not None else jpeg_bytes(640, 480), "image/jpeg")},
        headers=auth(token),
    )


def test_register_face_end_to_end(client: TestClient, admin_token: str, encoder: FakeEncoder) -> None:
    pid = _person(client, admin_token)
    encoder.faces = [_face()]
    created = _add_face(client, admin_token, pid)
    assert created.status_code == 201, created.text
    face_id = created.json()["id"]
    assert "embedding" not in created.json()

    person = client.get(f"/people/{pid}", headers=auth(admin_token)).json()
    assert person["face_count"] == 1
    assert [f["id"] for f in client.get(f"/people/{pid}/faces", headers=auth(admin_token)).json()] == [face_id]

    thumb = client.get(f"/people/{pid}/faces/{face_id}/image", headers=auth(admin_token))
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"
    assert thumb.headers["cache-control"] == "no-store"

    embeddings = client.get("/face-embeddings", headers=auth(admin_token)).json()
    assert embeddings == [{"person_id": pid, "name": "Aiman", "embedding": [0.1] * 512}]


@pytest.mark.parametrize(
    ("faces", "expected"),
    [
        ([], "No face found"),
        ([_face(10), _face(300)], "Found 2 faces"),
        ([_face(width=30)], "too small"),
    ],
)
def test_face_photo_rules(
    client: TestClient, admin_token: str, encoder: FakeEncoder, faces: list[DetectedFace], expected: str
) -> None:
    pid = _person(client, admin_token)
    encoder.faces = faces
    resp = _add_face(client, admin_token, pid)
    assert resp.status_code == 422
    assert expected in resp.json()["detail"]
    assert client.get(f"/people/{pid}", headers=auth(admin_token)).json()["face_count"] == 0


def test_face_upload_rejects_non_images_and_unknown_person(
    client: TestClient, admin_token: str, encoder: FakeEncoder
) -> None:
    pid = _person(client, admin_token)
    encoder.faces = [_face()]
    assert _add_face(client, admin_token, pid, b"definitely not a photo").status_code == 422
    assert _add_face(client, admin_token, 9999).status_code == 404


def test_face_data_is_admin_only(
    client: TestClient, admin_token: str, operator_token: str, ai_service_token: str, encoder: FakeEncoder
) -> None:
    pid = _person(client, admin_token)
    encoder.faces = [_face()]
    face_id = _add_face(client, admin_token, pid).json()["id"]

    for token in (operator_token, ai_service_token):
        assert _add_face(client, token, pid).status_code == 403
        assert client.get(f"/people/{pid}/faces", headers=auth(token)).status_code == 403
        assert client.get(f"/people/{pid}/faces/{face_id}/image", headers=auth(token)).status_code == 403
        assert client.delete(f"/people/{pid}/faces/{face_id}", headers=auth(token)).status_code == 403

    # Embeddings: the recognizer's service account may read them, operators may not.
    assert client.get("/face-embeddings", headers=auth(operator_token)).status_code == 403
    assert client.get("/face-embeddings", headers=auth(ai_service_token)).status_code == 200


def test_delete_face_and_person_remove_files(client: TestClient, admin_token: str, encoder: FakeEncoder) -> None:
    pid = _person(client, admin_token)
    encoder.faces = [_face()]
    first = _add_face(client, admin_token, pid).json()["id"]
    _add_face(client, admin_token, pid)

    h = auth(admin_token)
    files_before = {p.name for p in media_store.list_files("faces")}
    assert client.delete(f"/people/{pid}/faces/{first}", headers=h).status_code == 204
    assert client.get(f"/people/{pid}", headers=h).json()["face_count"] == 1
    assert client.get(f"/people/{pid}/faces/{first}/image", headers=h).status_code == 404

    assert client.delete(f"/people/{pid}", headers=h).status_code == 204
    files_after = {p.name for p in media_store.list_files("faces")}
    assert len(files_before - files_after) == 2
    assert client.get("/face-embeddings", headers=h).json() == []


def test_inactive_people_are_not_matched(client: TestClient, admin_token: str, encoder: FakeEncoder) -> None:
    from app.db.session import SessionLocal
    from app.models import Person

    pid = _person(client, admin_token)
    encoder.faces = [_face()]
    _add_face(client, admin_token, pid)
    with SessionLocal() as db:
        db.get(Person, pid).is_active = False
        db.commit()
    assert client.get("/face-embeddings", headers=auth(admin_token)).json() == []


def test_sighting_updates_last_seen_and_broadcasts(
    client: TestClient, admin_token: str, operator_token: str, ai_service_token: str, seeded: dict[str, int]
) -> None:
    pid = _person(client, admin_token)
    cam = seeded["camera_id"]
    body = {"camera_id": cam, "similarity": 0.71}

    assert client.post(f"/people/{pid}/sightings", json=body, headers=auth(operator_token)).status_code == 403
    with client.websocket_connect(f"/ws/alerts?token={operator_token}") as ws:
        resp = client.post(f"/people/{pid}/sightings", json=body, headers=auth(ai_service_token))
        msg = ws.receive_json()

    assert resp.status_code == 200, resp.text
    assert resp.json()["last_seen_camera_id"] == cam
    assert resp.json()["last_seen_at"] is not None
    assert msg["type"] == "person_seen"
    assert (msg["person_id"], msg["camera_id"], msg["similarity"]) == (pid, cam, 0.71)

    bad_camera = {"camera_id": 9999, "similarity": 0.5}
    assert client.post(f"/people/{pid}/sightings", json=bad_camera, headers=auth(ai_service_token)).status_code == 400
    bad_score = {"camera_id": cam, "similarity": 1.5}
    assert client.post(f"/people/{pid}/sightings", json=bad_score, headers=auth(ai_service_token)).status_code == 422
