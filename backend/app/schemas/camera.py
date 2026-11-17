from datetime import datetime

from pydantic import BaseModel, Field

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


class CameraOut(BaseModel):
    id: int
    name: str
    location: str | None
    stream_source: str
    status: CameraStatus
    last_seen_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
