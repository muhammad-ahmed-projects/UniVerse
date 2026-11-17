from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low", "medium", "high"]


class AlertCreate(BaseModel):
    camera_id: int = Field(gt=0)
    alert_type: str = Field(min_length=1, max_length=50)
    priority: Priority = "medium"
    message: str = Field(min_length=1, max_length=500)
    evidence_path: str | None = Field(default=None, max_length=500)
    extra_data: dict | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    alert_type: str
    priority: str
    message: str
    evidence_path: str | None
    extra_data: dict | None
    incident_id: int | None
    triggered_at: datetime
