from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low", "medium", "high"]


class AlertCreate(BaseModel):
    camera_id: int = Field(gt=0)
    alert_type: str = Field(min_length=1, max_length=50)
    priority: Priority = "medium"
    message: str = Field(min_length=1, max_length=500)
    extra_data: dict | None = None


class AlertImageOut(BaseModel):
    """Metadata only; the JPEG itself is GET /alerts/{alert_id}/images/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int
    captured_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    alert_type: str
    priority: str
    message: str
    extra_data: dict | None
    incident_id: int | None
    triggered_at: datetime
    images: list[AlertImageOut]
