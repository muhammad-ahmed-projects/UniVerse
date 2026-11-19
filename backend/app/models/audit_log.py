from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditLog(Base):
    """Who did what, when (proposal: Security & Privacy -> audit logs).

    Rows are append-only: nothing in the API edits or deletes them.
    actor_username is a snapshot, so the entry stays readable after the
    account is deleted (actor_id then becomes NULL).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Dotted verb, e.g. "auth.login_failed", "user.create", "face.view".
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
