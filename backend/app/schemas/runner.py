from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ScriptName = Literal["roi_loitering", "tamper_detection", "face_recognition", "camera_health"]


class RunnerStart(BaseModel):
    scripts: list[ScriptName] = Field(min_length=1, max_length=4)

    @field_validator("scripts")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("each analysis can be selected once")
        return value


class RunnerScriptOut(BaseModel):
    name: str
    pid: int
    running: bool
    exit_code: int | None
    # True when it was stopped from the dashboard (a crash leaves it False).
    stopped_by_user: bool
    started_at: datetime


class RunnerOut(BaseModel):
    camera_id: int
    running: bool
    # The camera's stream is a local USB webcam (only one analysis at a time).
    is_webcam: bool
    scripts: list[RunnerScriptOut]
    log: list[str]
