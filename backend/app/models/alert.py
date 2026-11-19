from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Alert(Base):
    """A raw AI-generated event. Alert types are intentionally a free
    string (not a DB enum) so new detection types can be added without a
    migration. Types the AI scripts emit: ROI_ENTRY, LOITERING,
    TAMPER_COVERED, TAMPER_MOVED, TAMPER_DEFOCUSED, CAMERA_OFFLINE,
    CAMERA_ONLINE, UNKNOWN_FACE.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Human verdict on the detection: "confirmed" (real event) or "false_alarm".
    # NULL = not reviewed yet. Feeds the false-alert rate / precision report.
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # selectin: list endpoints load every alert's images in one extra query, not one per alert.
    images: Mapped[list["AlertImage"]] = relationship(
        back_populates="alert",
        lazy="selectin",
        order_by="AlertImage.id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AlertImage(Base):
    """An evidence snapshot for an alert (the annotated camera frame at, and
    shortly after, the moment the alert fired). The JPEG lives on disk under
    MEDIA_DIR/evidence/; this row holds only its generated file name.
    """

    __tablename__ = "alert_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alert: Mapped[Alert] = relationship(back_populates="images")
