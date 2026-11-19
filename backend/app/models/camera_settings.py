from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CameraSettings(Base):
    """Per-camera configurable thresholds (Section 11: 'configurable
    rules', not hardcoded magic numbers). One row per camera, created
    with defaults on first read if it doesn't exist yet.
    """

    __tablename__ = "camera_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), unique=True, nullable=False)

    # ROI rectangle, as fractions of frame size (0.0-1.0) -- matches
    # app/ai/prototypes/roi_loitering.py's --roi format.
    roi_x1: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    roi_y1: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roi_x2: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    roi_y2: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    loiter_seconds: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)

    tamper_motion_threshold: Mapped[float] = mapped_column(Float, default=25.0, nullable=False)
    tamper_covered_brightness_ratio: Mapped[float] = mapped_column(Float, default=0.4, nullable=False)
    tamper_covered_sharpness_ratio: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    tamper_defocus_sharpness_ratio: Mapped[float] = mapped_column(Float, default=0.35, nullable=False)

    # Cosine similarity (0-1) a face must reach against a registered sample to
    # count as that person; below it the face is "Unknown". Higher = stricter.
    face_match_threshold: Mapped[float] = mapped_column(Float, default=0.45, nullable=False)

    # Unusual activity (roi_loitering.py). 0 turns a rule off.
    # People in view at once that count as a crowd.
    crowd_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # Speed, in frame widths per second, above which a person counts as running.
    running_speed: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    # Seconds a bag/suitcase stays still with nobody near it before an alert.
    abandoned_seconds: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    # Seconds a person's box must stay lying-down shaped (after standing) to count as a fall.
    fall_seconds: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
