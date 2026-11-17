from datetime import datetime

from pydantic import BaseModel, Field

ALLOWED_PRIORITIES = {"low", "medium", "high"}


class AlertCreate(BaseModel):
    camera_id: int
    alert_type: str = Field(min_length=1, max_length=50)
    priority: str = Field(default="medium", max_length=20)
    message: str = Field(min_length=1, max_length=500)
    evidence_path: str | None = Field(default=None, max_length=500)
    extra_data: dict | None = None


class AlertOut(BaseModel):
    id: int
    camera_id: int
    alert_type: str
    priority: str
    message: str
    evidence_path: str | None
    extra_data: dict | None
    incident_id: int | None
    triggered_at: datetime

    class Config:
        from_attributes = True
