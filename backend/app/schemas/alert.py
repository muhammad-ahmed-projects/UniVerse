from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low", "medium", "high"]
ReviewStatus = Literal["confirmed", "false_alarm"]


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
    review_status: ReviewStatus | None
    reviewed_by: int | None
    reviewed_at: datetime | None


class AlertReview(BaseModel):
    """null clears the verdict (back to unreviewed)."""

    review_status: ReviewStatus | None


class ReviewCounts(BaseModel):
    total: int
    confirmed: int
    false_alarm: int
    unreviewed: int
    # confirmed / (confirmed + false_alarm); None until something is reviewed.
    precision: float | None
    # false_alarm / (confirmed + false_alarm)
    false_alarm_rate: float | None


class ReviewStatsRow(ReviewCounts):
    alert_type: str


class ReviewStats(BaseModel):
    overall: ReviewCounts
    by_type: list[ReviewStatsRow]
