from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.camera import CameraStatus


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    stream_source: str = Field(min_length=1, max_length=500)


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    stream_source: str | None = Field(default=None, min_length=1, max_length=500)
    status: CameraStatus | None = None


class CameraHeartbeat(BaseModel):
    """Status report from a camera-health process. Only online/offline --
    'unknown' is the server's state for a camera nobody has reported on.
    """

    status: Literal["online", "offline"]


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str | None
    stream_source: str
    status: CameraStatus
    last_seen_at: datetime | None
    created_at: datetime

    @field_serializer("stream_source")
    def _mask_credentials(self, value: str) -> str:
        """IP-camera URLs often embed credentials (rtsp://user:pass@host/...).
        The API never needs to hand those back out, so the password is masked
        in every response; the AI scripts get the real source via --source.
        """
        parts = urlsplit(value)
        if not parts.password:
            return value
        host = parts.hostname or ""
        host = f"[{host}]" if ":" in host else host  # IPv6 literal
        port = f":{parts.port}" if parts.port else ""
        return urlunsplit(parts._replace(netloc=f"{parts.username}:***@{host}{port}"))
