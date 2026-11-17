"""Import every model here so Alembic's autogenerate sees the full schema."""
from app.models.alert import Alert
from app.models.camera import Camera, CameraStatus
from app.models.incident import Incident
from app.models.person import FaceEmbedding, Person
from app.models.user import User, UserRole

__all__ = [
    "Alert",
    "Camera",
    "CameraStatus",
    "Incident",
    "FaceEmbedding",
    "Person",
    "User",
    "UserRole",
]
