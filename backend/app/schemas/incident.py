from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import Priority

IncidentStatus = Literal["open", "acknowledged", "resolved"]


class IncidentCreate(BaseModel):
    camera_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: Priority = "medium"
    source_alert_id: int | None = Field(default=None, gt=0)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
