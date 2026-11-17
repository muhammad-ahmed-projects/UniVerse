from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    camera_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: str = Field(default="medium", max_length=20)
    source_alert_id: int | None = None


class IncidentOut(BaseModel):
    id: int
    camera_id: int
    title: str
    description: str | None
    status: str
    priority: str
    acknowledged_by: int | None
    acknowledged_at: datetime | None
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
