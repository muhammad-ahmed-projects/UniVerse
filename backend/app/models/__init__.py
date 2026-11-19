"""Import every model here so Alembic's autogenerate sees the full schema."""

from app.models.alert import Alert, AlertImage
from app.models.audit_log import AuditLog
from app.models.camera import Camera, CameraStatus
from app.models.camera_settings import CameraSettings
from app.models.incident import Incident
from app.models.person import FaceEmbedding, Person
from app.models.user import User, UserRole

__all__ = [
    "Alert",
    "AlertImage",
    "AuditLog",
    "Camera",
    "CameraStatus",
    "CameraSettings",
    "Incident",
    "FaceEmbedding",
    "Person",
    "User",
    "UserRole",
]
