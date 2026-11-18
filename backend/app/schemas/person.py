from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    notes: str | None
    is_active: bool
    created_at: datetime
    face_count: int
    last_seen_at: datetime | None
    last_seen_camera_id: int | None


class FaceSampleOut(BaseModel):
    """A registered face sample. The embedding itself is never returned here;
    the thumbnail is GET /people/{person_id}/faces/{id}/image (admin only).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    created_at: datetime


class FaceEmbeddingOut(BaseModel):
    """What the face_recognition script downloads to match against."""

    person_id: int
    name: str
    embedding: list[float]


class SightingCreate(BaseModel):
    camera_id: int = Field(gt=0)
    similarity: float = Field(ge=0, le=1)
