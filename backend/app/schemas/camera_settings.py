from pydantic import BaseModel, ConfigDict, Field, model_validator


class CameraSettingsUpdate(BaseModel):
    roi_x1: float = Field(ge=0.0, le=1.0, default=0.5)
    roi_y1: float = Field(ge=0.0, le=1.0, default=0.0)
    roi_x2: float = Field(ge=0.0, le=1.0, default=1.0)
    roi_y2: float = Field(ge=0.0, le=1.0, default=1.0)
    loiter_seconds: float = Field(gt=0, le=3600, default=5.0)
    tamper_motion_threshold: float = Field(gt=0, le=255, default=25.0)
    tamper_covered_brightness_ratio: float = Field(gt=0, le=1, default=0.4)
    tamper_covered_sharpness_ratio: float = Field(gt=0, le=1, default=0.3)
    tamper_defocus_sharpness_ratio: float = Field(gt=0, le=1, default=0.35)

    @model_validator(mode="after")
    def check_roi_ordering(self) -> "CameraSettingsUpdate":
        if self.roi_x1 >= self.roi_x2 or self.roi_y1 >= self.roi_y2:
            raise ValueError("roi_x1/roi_y1 must be less than roi_x2/roi_y2")
        return self


class CameraSettingsOut(CameraSettingsUpdate):
    model_config = ConfigDict(from_attributes=True)

    camera_id: int
