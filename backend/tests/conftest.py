"""Test setup: runs the real app against a separate Postgres database
(`universe_test` by default, or TEST_DATABASE_URL), never the dev DB.
Tables are created once per session and truncated after every test.
"""

import os
import tempfile
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

load_dotenv()

_explicit_url = os.getenv("TEST_DATABASE_URL")
_test_url = (
    make_url(_explicit_url) if _explicit_url else make_url(os.environ["DATABASE_URL"]).set(database="universe_test")
)
if "test" not in (_test_url.database or ""):
    raise RuntimeError(f"Refusing to run tests against non-test database {_test_url.database!r}")

# Must happen before any app module is imported: app.db.session builds its engine at import time.
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)
# Evidence/face files from tests go to a throwaway dir, never backend/media.
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="universe_test_media_")


def _ensure_test_database() -> None:
    admin_engine = create_engine(_test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _test_url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_test_url.database}"'))
    admin_engine.dispose()


_ensure_test_database()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Camera, User, UserRole  # noqa: E402
from app.services.frame_store import frame_store  # noqa: E402

ADMIN = ("admin_t", "admin-pass-123")
OPERATOR = ("operator_t", "operator-pass-123")
AI_SERVICE = ("ai_service_t", "ai-service-pass-123")


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    frame_store.clear()
    app.dependency_overrides.clear()


@pytest.fixture
def seeded() -> dict[str, int]:
    """Admin, operator and ai_service users, and one camera."""
    with SessionLocal() as db:
        db.add_all(
            [
                User(username=ADMIN[0], hashed_password=hash_password(ADMIN[1]), role=UserRole.ADMIN),
                User(
                    username=OPERATOR[0],
                    hashed_password=hash_password(OPERATOR[1]),
                    role=UserRole.SECURITY_OPERATOR,
                ),
                User(username=AI_SERVICE[0], hashed_password=hash_password(AI_SERVICE[1]), role=UserRole.AI_SERVICE),
            ]
        )
        camera = Camera(name="Cam A", stream_source="0")
        db.add(camera)
        db.commit()
        return {"camera_id": camera.id}


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _token(client: TestClient, creds: tuple[str, str]) -> str:
    resp = client.post("/auth/login", data={"username": creds[0], "password": creds[1]})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_token(client: TestClient, seeded: dict[str, int]) -> str:
    return _token(client, ADMIN)


@pytest.fixture
def operator_token(client: TestClient, seeded: dict[str, int]) -> str:
    return _token(client, OPERATOR)


@pytest.fixture
def ai_service_token(client: TestClient, seeded: dict[str, int]) -> str:
    return _token(client, AI_SERVICE)


def jpeg_bytes(width: int = 320, height: int = 240) -> bytes:
    """A real (tiny) JPEG for upload tests."""
    import cv2
    import numpy as np

    image = np.full((height, width, 3), 128, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", image)
    assert ok
    return buf.tobytes()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
