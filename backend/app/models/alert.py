from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

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
    evidence_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
