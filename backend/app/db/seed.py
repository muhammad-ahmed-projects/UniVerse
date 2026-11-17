"""Dev-data seed script. Run manually, not on every startup:
python -m app.db.seed
"""

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.camera import Camera, CameraStatus
from app.models.user import User, UserRole


def run() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username="admin").first():
            db.add(
                User(
                    username="admin",
                    email="admin@universe.local",
                    hashed_password=hash_password("admin123"),
                    role=UserRole.ADMIN,
                )
            )
        if not db.query(User).filter_by(username="operator").first():
            db.add(
                User(
                    username="operator",
                    email="operator@universe.local",
                    hashed_password=hash_password("operator123"),
                    role=UserRole.SECURITY_OPERATOR,
                )
            )
        if not db.query(Camera).filter_by(name="Test Camera 1").first():
            db.add(
                Camera(
                    name="Test Camera 1",
                    location="Mock office - entrance",
                    stream_source="0",
                    status=CameraStatus.UNKNOWN,
                )
            )
        if not db.query(Camera).filter_by(name="Test Camera 2").first():
            db.add(
                Camera(
                    name="Test Camera 2",
                    location="Mock office - restricted storage",
                    stream_source="1",
                    status=CameraStatus.UNKNOWN,
                )
            )
        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
